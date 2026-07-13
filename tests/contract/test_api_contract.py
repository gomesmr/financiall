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
