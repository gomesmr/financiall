from __future__ import annotations

import io

from src.services.sefaz_client import DadosNotaSefaz
from src.storage import db as storage_db
from src.worker import ocr_worker
from tests.helpers import gerar_chave_valida


def test_importar_nota_nova_via_url_grava_no_banco(app_e_db, client, monkeypatch):
    _, db_path = app_e_db
    monkeypatch.setattr(
        "src.services.importador.sefaz_client.buscar_dados_nota",
        lambda url: DadosNotaSefaz(
            emitente_nome="Farmácia Exemplo",
            data_emissao="2026-06-10",
            valor_total=1990,
            itens=[],
        ),
    )
    chave = gerar_chave_valida(numero="000000001")
    url = f"https://www.sefaz.sp.gov.br/nfce/qrcode?p={chave}|2|1|1|hash"

    resposta = client.post("/notas", json={"entrada": url})
    assert resposta.status_code == 201

    nota_no_banco = storage_db.buscar_por_chave_acesso(chave, db_path=db_path)
    assert nota_no_banco is not None
    assert nota_no_banco.emitente_nome == "Farmácia Exemplo"
    assert nota_no_banco.canal_origem.value == "url_chave"


def test_importar_nota_nova_via_chave_colada_com_espacos_grava_no_banco(app_e_db, client):
    _, db_path = app_e_db
    chave = gerar_chave_valida(numero="000000002")
    chave_com_espacos = f"  {chave[:20]} {chave[20:]}  "

    resposta = client.post("/notas", json={"entrada": chave_com_espacos})
    assert resposta.status_code == 201

    nota_no_banco = storage_db.buscar_por_chave_acesso(chave, db_path=db_path)
    assert nota_no_banco is not None
    assert nota_no_banco.status.value == "pendente_revisao"


def test_importar_entrada_invalida_nao_grava_nada(app_e_db, client):
    _, db_path = app_e_db
    resposta = client.post("/notas", json={"entrada": "nao-e-uma-chave"})
    assert resposta.status_code == 422
    assert storage_db.listar_notas(db_path=db_path) == []


def test_upload_foto_e_consulta_status_ate_concluido(app_e_db, client, monkeypatch):
    _, db_path = app_e_db
    chave = gerar_chave_valida(numero="000000003")
    texto_ocr = (
        "MERCADO EXEMPLO LTDA\n"
        "CNPJ: 12.345.678/0001-99\n"
        "Data emissao: 20/06/2026\n"
        "ARROZ 5KG               1,000    25,00\n"
        "VALOR TOTAL R$                   25,00\n"
        f"{chave}\n"
    )
    monkeypatch.setattr("src.worker.ocr_worker.ocr_client.reconhecer_texto", lambda caminho: texto_ocr)

    upload = client.post(
        "/notas/upload",
        data={"arquivo": (io.BytesIO(b"bytes-da-foto"), "cupom.jpg")},
        content_type="multipart/form-data",
    )
    assert upload.status_code == 202
    envio_id = upload.get_json()["envio_id"]

    status_antes = client.get(f"/envios/{envio_id}").get_json()
    assert status_antes["status"] == "pendente"

    processou = ocr_worker.processar_proximo_envio(db_path=db_path)
    assert processou is True

    status_depois = client.get(f"/envios/{envio_id}").get_json()
    assert status_depois["status"] == "concluido"
    assert status_depois["nota_status"] == "completa"
    assert status_depois["nota"]["chave_acesso"] == chave

    nota_no_banco = storage_db.buscar_por_chave_acesso(chave, db_path=db_path)
    assert nota_no_banco is not None
    assert nota_no_banco.canal_origem.value == "foto_pdf"


def test_mesma_nota_via_url_e_depois_via_foto_nao_duplica(app_e_db, client, monkeypatch):
    """US3 cenario 1: mesma chave por dois canais diferentes nao duplica."""
    _, db_path = app_e_db
    chave = gerar_chave_valida(numero="000000004")

    monkeypatch.setattr(
        "src.services.importador.sefaz_client.buscar_dados_nota",
        lambda url: DadosNotaSefaz(),
    )
    url = f"https://www.sefaz.sp.gov.br/nfce/qrcode?p={chave}|2|1|1|hash"
    resposta_url = client.post("/notas", json={"entrada": url})
    assert resposta_url.status_code == 201

    texto_ocr_com_a_mesma_chave = f"LOJA QUALQUER\n{chave}\n"
    monkeypatch.setattr(
        "src.worker.ocr_worker.ocr_client.reconhecer_texto", lambda caminho: texto_ocr_com_a_mesma_chave
    )
    upload = client.post(
        "/notas/upload",
        data={"arquivo": (io.BytesIO(b"outra-foto-da-mesma-nota"), "cupom2.jpg")},
        content_type="multipart/form-data",
    )
    envio_id = upload.get_json()["envio_id"]
    ocr_worker.processar_proximo_envio(db_path=db_path)

    status_envio = client.get(f"/envios/{envio_id}").get_json()
    assert status_envio["nota"]["chave_acesso"] == chave

    notas = storage_db.listar_notas(db_path=db_path)
    notas_com_essa_chave = [n for n in notas if n.chave_acesso == chave]
    assert len(notas_com_essa_chave) == 1


def test_fonte_sefaz_indisponivel_ainda_registra_nota_sem_erro_5xx(app_e_db, client, monkeypatch):
    """US4 cenario 1: fonte externa indisponivel nunca impede o registro."""
    from src.services import sefaz_client

    def _indisponivel(url):
        raise sefaz_client.BuscaSefazIndisponivelError("timeout simulado")

    monkeypatch.setattr("src.services.importador.sefaz_client.buscar_dados_nota", _indisponivel)

    chave = gerar_chave_valida(numero="000000005")
    url = f"https://www.sefaz.sp.gov.br/nfce/qrcode?p={chave}|2|1|1|hash"
    resposta = client.post("/notas", json={"entrada": url})

    assert resposta.status_code == 201
    corpo = resposta.get_json()
    assert corpo["status"] == "pendente_revisao"


def test_foto_ilegivel_ainda_conclui_processamento_sem_erro(app_e_db, client, monkeypatch):
    """US4 cenario 3: OCR sem nenhum campo utilizavel ainda registra o envio."""
    _, db_path = app_e_db

    def _ocr_sem_nada_util(caminho):
        return "###   ...   ilegivel   ---"

    monkeypatch.setattr("src.worker.ocr_worker.ocr_client.reconhecer_texto", _ocr_sem_nada_util)

    upload = client.post(
        "/notas/upload",
        data={"arquivo": (io.BytesIO(b"foto-borrada"), "borrada.jpg")},
        content_type="multipart/form-data",
    )
    envio_id = upload.get_json()["envio_id"]

    processou = ocr_worker.processar_proximo_envio(db_path=db_path)
    assert processou is True

    status = client.get(f"/envios/{envio_id}").get_json()
    assert status["status"] == "concluido"
    assert status["nota_status"] == "pendente_revisao"
    assert status["mensagem"] == "Processamento concluído com dados incompletos."


def test_listar_notas_em_meses_diferentes_com_e_sem_filtro(app_e_db, client):
    chave_junho = gerar_chave_valida(numero="000000020", aamm="2606")
    chave_maio = gerar_chave_valida(numero="000000021", aamm="2605")
    client.post("/notas", json={"entrada": chave_junho})
    client.post("/notas", json={"entrada": chave_maio})

    todas = client.get("/notas").get_json()["notas"]
    assert len(todas) == 2

    so_junho = client.get("/notas?mes=2026-06").get_json()["notas"]
    assert len(so_junho) == 1
    assert so_junho[0]["chave_acesso"] == chave_junho


def test_resumo_historico_com_notas_em_meses_diferentes(app_e_db, client):
    chave_jan = gerar_chave_valida(numero="000000030", aamm="2501")
    chave_fev = gerar_chave_valida(numero="000000031", aamm="2502")
    chave_fev_2 = gerar_chave_valida(numero="000000032", aamm="2502")
    client.post("/notas", json={"entrada": chave_jan})
    client.post("/notas", json={"entrada": chave_fev})
    client.post("/notas", json={"entrada": chave_fev_2})

    resposta = client.get("/notas/resumo/historico")
    corpo = resposta.get_json()

    por_mes = {m["mes"]: m for m in corpo["meses"]}
    assert por_mes["2025-01"]["quantidade_notas"] == 1
    assert por_mes["2025-02"]["quantidade_notas"] == 2
    assert corpo["meses"][0]["mes"] == "2025-02"  # mais recente primeiro
