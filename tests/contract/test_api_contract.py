from __future__ import annotations

import io
from datetime import date

from src.services import sefaz_client
from tests.helpers import gerar_chave_valida


def _dados_sefaz_completos():
    return sefaz_client.DadosNotaSefaz(
        emitente_nome="Mercado Exemplo Ltda",
        data_emissao="2026-06-15",
        valor_total=4590,
        itens=[
            {
                "codigo_item": "123",
                "descricao": "Produto Exemplo",
                "quantidade": 1.0,
                "valor_unitario": 4590,
                "valor_total_item": 4590,
            }
        ],
    )


def test_post_notas_entrada_vazia_retorna_422(client):
    resposta = client.post("/notas", json={"entrada": ""})
    assert resposta.status_code == 422
    assert "erro" in resposta.get_json()


def test_post_notas_chave_invalida_retorna_422_com_mensagem_em_portugues(client):
    resposta = client.post("/notas", json={"entrada": "12345"})
    corpo = resposta.get_json()
    assert resposta.status_code == 422
    assert corpo["erro"] == 'Não foi possível identificar uma chave de acesso válida de 44 dígitos em "12345".'


def test_post_notas_chave_colada_valida_sem_fonte_externa_e_pendente_revisao(client):
    chave = gerar_chave_valida()
    resposta = client.post("/notas", json={"entrada": chave})
    corpo = resposta.get_json()
    assert resposta.status_code == 201
    assert corpo["status"] == "pendente_revisao"
    assert corpo["nota"]["chave_acesso"] == chave
    assert corpo["mensagem"] == "Nota importada com dados parciais (pendente de revisão)."


def test_post_notas_url_com_sefaz_com_sucesso_retorna_completa(client, monkeypatch):
    monkeypatch.setattr(
        "src.services.importador.sefaz_client.buscar_dados_nota",
        lambda url: _dados_sefaz_completos(),
    )
    chave = gerar_chave_valida()
    url = f"https://www.sefaz.sp.gov.br/nfce/qrcode?p={chave}|2|1|1|abcdef"
    resposta = client.post("/notas", json={"entrada": url})
    corpo = resposta.get_json()
    assert resposta.status_code == 201
    assert corpo["status"] == "completa"
    assert corpo["mensagem"] == "Nota importada com sucesso."
    assert corpo["nota"]["emitente_nome"] == "Mercado Exemplo Ltda"
    assert len(corpo["nota"]["itens"]) == 1


def test_post_notas_chave_ja_registrada_retorna_200_com_chave_mascarada(client):
    chave = gerar_chave_valida()
    primeira = client.post("/notas", json={"entrada": chave})
    assert primeira.status_code == 201

    segunda = client.post("/notas", json={"entrada": chave})
    corpo = segunda.get_json()
    assert segunda.status_code == 200
    assert corpo["status"] == "ja_registrada"
    assert corpo["nota"]["chave_acesso"] == f"...{chave[-4:]}"
    assert "Nota já registrada em" in corpo["mensagem"]


def test_post_notas_upload_arquivo_valido_retorna_202_pendente(client):
    resposta = client.post(
        "/notas/upload",
        data={"arquivo": (io.BytesIO(b"conteudo-fake-de-foto"), "cupom.jpg")},
        content_type="multipart/form-data",
    )
    corpo = resposta.get_json()
    assert resposta.status_code == 202
    assert corpo["status"] == "pendente"
    assert isinstance(corpo["envio_id"], int)
    assert f"/envios/{corpo['envio_id']}" in corpo["mensagem"]


def test_post_notas_upload_tipo_nao_suportado_retorna_415(client):
    resposta = client.post(
        "/notas/upload",
        data={"arquivo": (io.BytesIO(b"texto qualquer"), "documento.txt")},
        content_type="multipart/form-data",
    )
    corpo = resposta.get_json()
    assert resposta.status_code == 415
    assert "erro" in corpo


def test_post_notas_upload_sem_arquivo_retorna_400(client):
    resposta = client.post("/notas/upload", data={}, content_type="multipart/form-data")
    corpo = resposta.get_json()
    assert resposta.status_code == 400
    assert corpo["erro"] == "Nenhum arquivo foi enviado."


def test_get_envio_inexistente_retorna_404(client):
    resposta = client.get("/envios/999999")
    assert resposta.status_code == 404
    assert resposta.get_json()["erro"] == "Envio não encontrado."


def test_get_envio_recem_criado_retorna_pendente(client):
    upload = client.post(
        "/notas/upload",
        data={"arquivo": (io.BytesIO(b"foto"), "cupom.jpg")},
        content_type="multipart/form-data",
    )
    envio_id = upload.get_json()["envio_id"]

    resposta = client.get(f"/envios/{envio_id}")
    corpo = resposta.get_json()
    assert resposta.status_code == 200
    assert corpo["status"] == "pendente"


def test_get_envio_concluido_completo(client, monkeypatch, app_e_db):
    from src.worker import ocr_worker

    _, db_path = app_e_db
    chave = gerar_chave_valida(numero="000000010")
    texto_ocr = (
        "LOJA EXEMPLO\n"
        "CNPJ: 12.345.678/0001-99\n"
        "Data emissao: 10/06/2026\n"
        "ITEM UM                 1,000    10,00\n"
        "VALOR TOTAL R$                   10,00\n"
        f"{chave}\n"
    )
    monkeypatch.setattr("src.worker.ocr_worker.ocr_client.reconhecer_texto_de_imagem", lambda imagem: texto_ocr)
    monkeypatch.setattr("src.worker.ocr_worker._imagens_do_envio", lambda envio: ["imagem-fake"])

    upload = client.post(
        "/notas/upload",
        data={"arquivo": (io.BytesIO(b"foto"), "cupom.jpg")},
        content_type="multipart/form-data",
    )
    envio_id = upload.get_json()["envio_id"]
    ocr_worker.processar_proximo_envio(db_path=db_path)

    resposta = client.get(f"/envios/{envio_id}")
    corpo = resposta.get_json()
    assert resposta.status_code == 200
    assert corpo["status"] == "concluido"
    assert corpo["nota_status"] == "completa"
    assert corpo["nota"]["chave_acesso"] == chave


def test_get_envio_concluido_com_dados_incompletos(client, monkeypatch, app_e_db):
    from src.worker import ocr_worker

    _, db_path = app_e_db
    monkeypatch.setattr("src.worker.ocr_worker.ocr_client.reconhecer_texto_de_imagem", lambda imagem: "ilegivel")
    monkeypatch.setattr("src.worker.ocr_worker._imagens_do_envio", lambda envio: ["imagem-fake"])

    upload = client.post(
        "/notas/upload",
        data={"arquivo": (io.BytesIO(b"foto"), "cupom_ruim.jpg")},
        content_type="multipart/form-data",
    )
    envio_id = upload.get_json()["envio_id"]
    ocr_worker.processar_proximo_envio(db_path=db_path)

    resposta = client.get(f"/envios/{envio_id}")
    corpo = resposta.get_json()
    assert resposta.status_code == 200
    assert corpo["status"] == "concluido"
    assert corpo["nota_status"] == "pendente_revisao"
    assert corpo["mensagem"] == "Processamento concluído com dados incompletos."


def test_get_notas_base_vazia_retorna_lista_vazia(client):
    resposta = client.get("/notas")
    assert resposta.status_code == 200
    assert resposta.get_json() == {"notas": []}


def test_get_notas_com_filtro_de_mes(client):
    chave_junho = gerar_chave_valida(numero="000000011", aamm="2606")
    chave_maio = gerar_chave_valida(numero="000000012", aamm="2605")
    client.post("/notas", json={"entrada": chave_junho})
    client.post("/notas", json={"entrada": chave_maio})

    resposta = client.get("/notas?mes=2026-06")
    corpo = resposta.get_json()
    assert resposta.status_code == 200
    assert len(corpo["notas"]) == 1
    assert corpo["notas"][0]["chave_acesso"] == chave_junho


def _aamm_do_mes_corrente() -> str:
    hoje = date.today()
    return f"{hoje.year % 100:02d}{hoje.month:02d}"


def test_get_resumo_mes_atual_sem_notas(client):
    resposta = client.get("/notas/resumo/mes-atual")
    corpo = resposta.get_json()
    assert resposta.status_code == 200
    assert corpo["total_gasto"] is None
    assert corpo["quantidade_notas"] == 0
    assert corpo["parcial"] is True
    assert corpo["mensagem"] == "Nenhuma nota importada no mês corrente."


def test_get_resumo_mes_atual_com_notas(client):
    chave = gerar_chave_valida(numero="000000013", aamm=_aamm_do_mes_corrente())
    client.post("/notas", json={"entrada": chave})

    resposta = client.get("/notas/resumo/mes-atual")
    corpo = resposta.get_json()
    assert resposta.status_code == 200
    assert corpo["quantidade_notas"] == 1
    assert corpo["parcial"] is True
    assert corpo["mensagem"] == "Total parcial — reflete apenas notas fiscais importadas."


def test_get_resumo_historico_sem_notas(client):
    resposta = client.get("/notas/resumo/historico")
    corpo = resposta.get_json()
    assert resposta.status_code == 200
    assert corpo == {"meses": [], "parcial": True}


def test_get_resumo_historico_com_notas_de_mes_anterior(client):
    chave = gerar_chave_valida(numero="000000014", aamm="2501")
    client.post("/notas", json={"entrada": chave})

    resposta = client.get("/notas/resumo/historico")
    corpo = resposta.get_json()
    assert resposta.status_code == 200
    assert corpo["parcial"] is True
    assert any(m["mes"] == "2025-01" for m in corpo["meses"])


def test_pagina_upload_carrega(client):
    resposta = client.get("/")
    assert resposta.status_code == 200
    assert b"financiALL" in resposta.data
    assert resposta.content_type.startswith("text/html")


def test_get_notas_inclui_itens_da_nota(client, monkeypatch):
    """Regressão: GET /notas esquecia de buscar os itens de cada nota,
    sempre retornando `itens: []` mesmo quando a nota tinha itens."""
    monkeypatch.setattr(
        "src.services.importador.sefaz_client.buscar_dados_nota",
        lambda url: _dados_sefaz_completos(),
    )
    chave = gerar_chave_valida(numero="000000015")
    url = f"https://www.sefaz.sp.gov.br/nfce/qrcode?p={chave}|2|1|1|hash"
    client.post("/notas", json={"entrada": url})

    resposta = client.get("/notas")
    corpo = resposta.get_json()
    assert len(corpo["notas"]) == 1
    assert len(corpo["notas"][0]["itens"]) == 1
    assert corpo["notas"][0]["itens"][0]["descricao"] == "Produto Exemplo"


def test_pagina_ver_notas_carrega_vazia(client):
    resposta = client.get("/ver/notas")
    assert resposta.status_code == 200
    assert "Nenhuma nota importada" in resposta.get_data(as_text=True)


def test_pagina_ver_notas_lista_nota_importada(client):
    chave = gerar_chave_valida(numero="000000016")
    client.post("/notas", json={"entrada": chave})
    resposta = client.get("/ver/notas")
    texto = resposta.get_data(as_text=True)
    assert resposta.status_code == 200
    assert chave not in texto  # pagina nao expoe a chave crua, so os campos exibidos
    assert "pendente de revisão" in texto


def test_pagina_ver_resumo_inclui_graficos_com_notas_em_varios_meses(client, monkeypatch):
    monkeypatch.setattr(
        "src.services.importador.sefaz_client.buscar_dados_nota",
        lambda url: _dados_sefaz_completos(),
    )
    for numero, aamm in [("000000080", "2501"), ("000000081", "2502"), ("000000082", "2503")]:
        chave = gerar_chave_valida(numero=numero, aamm=aamm)
        url = f"https://www.sefaz.sp.gov.br/nfce/qrcode?p={chave}|2|1|1|hash"
        client.post("/notas", json={"entrada": url})

    resposta = client.get("/ver/resumo")
    texto = resposta.get_data(as_text=True)
    assert resposta.status_code == 200
    assert 'id="grafico-pizza"' in texto
    assert 'id="grafico-barras"' in texto
    assert "plotly-basic.min.js" in texto


def test_pagina_ver_resumo_carrega(client):
    resposta = client.get("/ver/resumo")
    assert resposta.status_code == 200
    assert "Resumo de gastos" in resposta.get_data(as_text=True)


def test_pagina_ver_envio_pendente_tem_meta_refresh(client):
    upload = client.post(
        "/notas/upload",
        data={"arquivo": (io.BytesIO(b"foto"), "cupom.jpg")},
        content_type="multipart/form-data",
    )
    envio_id = upload.get_json()["envio_id"]
    resposta = client.get(f"/ver/envios/{envio_id}")
    texto = resposta.get_data(as_text=True)
    assert resposta.status_code == 200
    assert "http-equiv=\"refresh\"" in texto


def test_pagina_ver_envio_inexistente_retorna_404(client):
    resposta = client.get("/ver/envios/999999")
    assert resposta.status_code == 404
    assert "não encontrado" in resposta.get_data(as_text=True)


def test_pagina_ver_notas_linha_e_clicavel_para_o_detalhe(client):
    """Regressão: a listagem deve linkar cada linha para /ver/notas/<id>,
    sem vazar a representação crua do enum de status/canal no HTML."""
    chave = gerar_chave_valida(numero="000000017")
    resposta_import = client.post("/notas", json={"entrada": chave})
    nota_id = resposta_import.get_json()["nota"]["id"]

    resposta = client.get("/ver/notas")
    texto = resposta.get_data(as_text=True)
    assert resposta.status_code == 200
    assert f"/ver/notas/{nota_id}" in texto
    assert "linha-clicavel" in texto
    assert "StatusNota" not in texto
    assert "CanalOrigem" not in texto


def test_pagina_nota_detalhe_mostra_itens(client, monkeypatch):
    monkeypatch.setattr(
        "src.services.importador.sefaz_client.buscar_dados_nota",
        lambda url: _dados_sefaz_completos(),
    )
    chave = gerar_chave_valida(numero="000000018")
    url = f"https://www.sefaz.sp.gov.br/nfce/qrcode?p={chave}|2|1|1|hash"
    resposta_import = client.post("/notas", json={"entrada": url})
    nota_id = resposta_import.get_json()["nota"]["id"]

    resposta = client.get(f"/ver/notas/{nota_id}")
    texto = resposta.get_data(as_text=True)
    assert resposta.status_code == 200
    assert "Produto Exemplo" in texto
    assert "StatusNota" not in texto
    assert "CanalOrigem" not in texto


def test_pagina_nota_detalhe_inexistente_retorna_404(client):
    resposta = client.get("/ver/notas/999999")
    assert resposta.status_code == 404
    assert "não encontrada" in resposta.get_data(as_text=True)


def test_delete_nota_inexistente_retorna_404(client):
    resposta = client.delete("/notas/999999")
    corpo = resposta.get_json()
    assert resposta.status_code == 404
    assert corpo["erro"] == "Nota não encontrada."


def test_pagina_categorias_vazia_mostra_mensagem(client):
    resposta = client.get("/ver/categorias")
    assert resposta.status_code == 200
    assert "Nenhuma categoria criada" in resposta.get_data(as_text=True)


def test_pagina_categorias_lista_categoria_criada(client):
    client.post("/categorias", json={"nome": "Lazer"})
    resposta = client.get("/ver/categorias")
    texto = resposta.get_data(as_text=True)
    assert resposta.status_code == 200
    assert "Lazer" in texto


def test_post_categorias_com_parent_id_cria_subcategoria(client):
    resposta_topo = client.post("/categorias", json={"nome": "Alimentação"})
    topo_id = resposta_topo.get_json()["categoria"]["id"]

    resposta = client.post("/categorias", json={"nome": "Mercearia seca", "parent_id": topo_id})
    corpo = resposta.get_json()

    assert resposta.status_code == 201
    assert corpo["categoria"]["parent_id"] == topo_id


def test_post_categorias_parent_id_de_subcategoria_retorna_422(client):
    resposta_topo = client.post("/categorias", json={"nome": "Alimentação"})
    topo_id = resposta_topo.get_json()["categoria"]["id"]
    resposta_sub = client.post("/categorias", json={"nome": "Mercearia seca", "parent_id": topo_id})
    sub_id = resposta_sub.get_json()["categoria"]["id"]

    resposta = client.post("/categorias", json={"nome": "Nível 3", "parent_id": sub_id})

    assert resposta.status_code == 422


def test_post_categorias_quase_duplicata_retorna_409_com_sugestao(client):
    resposta_original = client.post("/categorias", json={"nome": "Mercearia Seca"})
    original_id = resposta_original.get_json()["categoria"]["id"]

    resposta = client.post("/categorias", json={"nome": "Mercearia"})
    corpo = resposta.get_json()

    assert resposta.status_code == 409
    assert corpo["sugestao"]["id"] == original_id


def test_post_categorias_quase_duplicata_com_forcar_cria_mesmo_assim(client):
    client.post("/categorias", json={"nome": "Mercearia Seca"})

    resposta = client.post("/categorias", json={"nome": "Mercearia", "forcar": True})

    assert resposta.status_code == 201


def _importar_historico_com_um_item(db_path, tmp_path, descricao: str, sufixo_chave: str):
    import json

    from src.services.importar_historico import importar_historico

    chave = gerar_chave_valida(numero=sufixo_chave)
    dados = {
        chave: {
            "data_emissao": "10/06/2026",
            "total": 10.0,
            "itens": [{"descricao": descricao, "qtd": 1, "vl_unit": 10.0, "vl_total": 10.0}],
        }
    }
    arquivo = tmp_path / f"historico_{sufixo_chave}.json"
    arquivo.write_text(json.dumps(dados), encoding="utf-8")
    importar_historico(str(arquivo), db_path=db_path)


def test_get_itens_pendentes_agrupa_e_inclui_resumo(client, app_e_db, tmp_path):
    _, db_path = app_e_db
    _importar_historico_com_um_item(db_path, tmp_path, "Item Pendente", "000000071")

    resposta = client.get("/itens/pendentes")
    corpo = resposta.get_json()

    assert resposta.status_code == 200
    assert corpo["resumo"]["total_pendente"] == 1
    assert corpo["grupos"][0]["descricao_normalizada"] == "ITEM PENDENTE"


def test_post_classificar_grupo_categoria_inexistente_retorna_422(client):
    resposta = client.post(
        "/itens/pendentes/classificar-grupo",
        json={"descricao_normalizada": "QUALQUER", "categoria_id": 999},
    )
    assert resposta.status_code == 422
    assert resposta.get_json()["erro"] == "Categoria não encontrada."


def test_post_classificar_grupo_sucesso(client, app_e_db, tmp_path):
    _, db_path = app_e_db
    _importar_historico_com_um_item(db_path, tmp_path, "Item Grupo", "000000072")
    categoria_id = client.post("/categorias", json={"nome": "Alimentação"}).get_json()["categoria"]["id"]

    resposta = client.post(
        "/itens/pendentes/classificar-grupo",
        json={"descricao_normalizada": "ITEM GRUPO", "categoria_id": categoria_id},
    )
    corpo = resposta.get_json()

    assert resposta.status_code == 200
    assert corpo["quantidade_itens_afetados"] == 1


def test_put_item_categoria_item_inexistente_retorna_404(client):
    resposta = client.put("/itens/999999/categoria", json={"categoria_id": 1})
    assert resposta.status_code == 404
    assert resposta.get_json()["erro"] == "Item não encontrado."


def test_put_item_categoria_sucesso(client, app_e_db, tmp_path):
    _, db_path = app_e_db
    _importar_historico_com_um_item(db_path, tmp_path, "Item Individual", "000000073")
    categoria_id = client.post("/categorias", json={"nome": "Alimentação"}).get_json()["categoria"]["id"]
    item_id = client.get("/itens/pendentes").get_json()["grupos"][0]["exemplo_item_id"]

    resposta = client.put(f"/itens/{item_id}/categoria", json={"categoria_id": categoria_id})

    assert resposta.status_code == 200


def test_pagina_ver_pendentes_carrega(client):
    resposta = client.get("/ver/pendentes")
    assert resposta.status_code == 200
    assert "pendente" in resposta.get_data(as_text=True).lower()


def test_get_impacto_correcao_fonte_item_inexistente_retorna_404(client):
    resposta = client.get("/itens/999999/impacto-correcao-fonte")
    assert resposta.status_code == 404
    assert resposta.get_json()["erro"] == "Item não encontrado."


def test_get_impacto_correcao_fonte_sucesso(client, app_e_db, tmp_path):
    _, db_path = app_e_db
    _importar_historico_com_um_item(db_path, tmp_path, "Item Fonte", "000000074")
    categoria_id = client.post("/categorias", json={"nome": "Alimentação"}).get_json()["categoria"]["id"]
    item_id = client.get("/itens/pendentes").get_json()["grupos"][0]["exemplo_item_id"]
    client.put(f"/itens/{item_id}/categoria", json={"categoria_id": categoria_id})

    resposta = client.get(f"/itens/{item_id}/impacto-correcao-fonte")
    corpo = resposta.get_json()

    assert resposta.status_code == 200
    assert corpo["descricao_normalizada"] == "ITEM FONTE"
    assert corpo["quantidade_itens_afetados"] == 1


def test_post_corrigir_fonte_item_inexistente_retorna_404(client):
    resposta = client.post("/itens/999999/corrigir-fonte", json={"categoria_id": 1})
    assert resposta.status_code == 404
    assert resposta.get_json()["erro"] == "Item não encontrado."


def test_post_corrigir_fonte_categoria_inexistente_retorna_422(client, app_e_db, tmp_path):
    _, db_path = app_e_db
    _importar_historico_com_um_item(db_path, tmp_path, "Item Fonte 2", "000000075")
    item_id = client.get("/itens/pendentes").get_json()["grupos"][0]["exemplo_item_id"]

    resposta = client.post(f"/itens/{item_id}/corrigir-fonte", json={"categoria_id": 999})

    assert resposta.status_code == 422
    assert resposta.get_json()["erro"] == "Categoria não encontrada."


def test_post_corrigir_fonte_sucesso(client, app_e_db, tmp_path):
    _, db_path = app_e_db
    _importar_historico_com_um_item(db_path, tmp_path, "Item Fonte 3", "000000076")
    categoria_errada_id = client.post("/categorias", json={"nome": "Errada"}).get_json()["categoria"]["id"]
    categoria_certa_id = client.post("/categorias", json={"nome": "Certa"}).get_json()["categoria"]["id"]
    item_id = client.get("/itens/pendentes").get_json()["grupos"][0]["exemplo_item_id"]
    client.put(f"/itens/{item_id}/categoria", json={"categoria_id": categoria_errada_id})

    resposta = client.post(f"/itens/{item_id}/corrigir-fonte", json={"categoria_id": categoria_certa_id})
    corpo = resposta.get_json()

    assert resposta.status_code == 200
    assert corpo["quantidade_itens_afetados"] == 1


def test_pagina_ver_notas_mostra_titular_e_filtra(client, app_e_db, tmp_path):
    import json

    from src.services.importar_historico import importar_historico

    _, db_path = app_e_db
    chave = gerar_chave_valida(numero="000000063")
    dados = {
        chave: {
            "emitente": "Loja Exemplo",
            "cnpj": "12.345.678/0001-99",
            "uf": "SP",
            "data_emissao": "01/01/2025",
            "total": 10.0,
            "itens": [],
            "conta": "cristine",
        }
    }
    arquivo = tmp_path / "historico.json"
    arquivo.write_text(json.dumps(dados), encoding="utf-8")

    importar_historico(str(arquivo), db_path=db_path)

    resposta = client.get("/ver/notas")
    assert "Cristine" in resposta.get_data(as_text=True)

    filtrada = client.get("/ver/notas?titular=marcelo")
    assert "Nenhuma nota importada" in filtrada.get_data(as_text=True) or chave not in filtrada.get_data(
        as_text=True
    )


def test_delete_nota_existente_retorna_200_com_mensagem(client):
    chave = gerar_chave_valida(numero="000000019")
    resposta_import = client.post("/notas", json={"entrada": chave})
    nota_id = resposta_import.get_json()["nota"]["id"]

    resposta = client.delete(f"/notas/{nota_id}")
    corpo = resposta.get_json()
    assert resposta.status_code == 200
    assert corpo["mensagem"] == "Nota excluída com sucesso."


def test_post_qrcode_frame_com_qrcode_valido_retorna_entrada(client):
    import qrcode as qrcode_lib

    chave = gerar_chave_valida(numero="000000920")
    url = f"https://www.sefaz.sp.gov.br/nfce/qrcode?p={chave}|2|1|1|hash"
    imagem_qrcode = qrcode_lib.make(url).convert("RGB")
    buffer = io.BytesIO()
    imagem_qrcode.save(buffer, format="PNG")

    resposta = client.post(
        "/notas/qrcode-frame", data=buffer.getvalue(), content_type="image/png"
    )
    assert resposta.status_code == 200
    assert resposta.get_json() == {"entrada": url}


def test_post_qrcode_frame_sem_qrcode_retorna_entrada_nula(client):
    from PIL import Image

    imagem_em_branco = Image.new("RGB", (200, 200), color="white")
    buffer = io.BytesIO()
    imagem_em_branco.save(buffer, format="PNG")

    resposta = client.post(
        "/notas/qrcode-frame", data=buffer.getvalue(), content_type="image/png"
    )
    assert resposta.status_code == 200
    assert resposta.get_json() == {"entrada": None}


def test_post_qrcode_frame_com_corpo_invalido_retorna_415(client):
    resposta = client.post(
        "/notas/qrcode-frame", data=b"nao e uma imagem", content_type="image/jpeg"
    )
    assert resposta.status_code == 415
    assert "erro" in resposta.get_json()
