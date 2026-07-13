from __future__ import annotations

import pytest

from src.services import fila_processamento
from src.storage import db as storage_db
from src.worker import ocr_worker


@pytest.fixture()
def db_path(tmp_path):
    caminho = str(tmp_path / "financiall.db")
    storage_db.init_db(caminho)
    return caminho


@pytest.fixture()
def upload_dir(tmp_path):
    caminho = tmp_path / "uploads"
    caminho.mkdir()
    return str(caminho)


def test_enfileirar_envio_grava_arquivo_e_insere_pendente(db_path, upload_dir):
    envio_id = fila_processamento.enfileirar_envio(
        "cupom.jpg", b"conteudo-fake-da-imagem", db_path=db_path, upload_dir=upload_dir
    )
    envio = storage_db.buscar_envio_por_id(envio_id, db_path=db_path)
    assert envio["status"] == "pendente"
    assert envio["tipo_arquivo"] == "foto"
    import os

    assert os.path.exists(envio["caminho_arquivo"])


def test_enfileirar_envio_tipo_nao_suportado_levanta_erro(db_path, upload_dir):
    with pytest.raises(fila_processamento.TipoArquivoNaoSuportadoError):
        fila_processamento.enfileirar_envio(
            "documento.txt", b"conteudo", db_path=db_path, upload_dir=upload_dir
        )


def test_calcular_hash_conteudo_e_deterministico():
    assert fila_processamento.calcular_hash_conteudo(b"abc") == fila_processamento.calcular_hash_conteudo(b"abc")
    assert fila_processamento.calcular_hash_conteudo(b"abc") != fila_processamento.calcular_hash_conteudo(b"abd")


def test_reconciliar_fila_apos_reinicio_reverte_processando_para_pendente(db_path, upload_dir):
    envio_id = fila_processamento.enfileirar_envio("cupom.png", b"x", db_path=db_path, upload_dir=upload_dir)
    storage_db.atualizar_status_envio(envio_id, "processando", db_path=db_path)

    revertidos = fila_processamento.reconciliar_fila_apos_reinicio(db_path=db_path)

    assert revertidos == 1
    envio = storage_db.buscar_envio_por_id(envio_id, db_path=db_path)
    assert envio["status"] == "pendente"


def test_processar_proximo_envio_fila_vazia_retorna_false(db_path):
    assert ocr_worker.processar_proximo_envio(db_path=db_path) is False


def test_processar_proximo_envio_sucesso_grava_nota_completa(db_path, upload_dir, monkeypatch):
    from tests.helpers import gerar_chave_valida

    chave = gerar_chave_valida()
    texto_ocr = (
        "FARMACIA EXEMPLO LTDA\n"
        "CNPJ: 12.345.678/0001-99\n"
        "Data emissao: 15/06/2026\n"
        "DIPIRONA 500MG          1,000    12,50\n"
        "VALOR TOTAL R$                   12,50\n"
        f"{chave}\n"
    )
    monkeypatch.setattr("src.worker.ocr_worker.ocr_client.reconhecer_texto_de_imagem", lambda imagem: texto_ocr)
    monkeypatch.setattr("src.worker.ocr_worker._imagens_do_envio", lambda envio: ["imagem-fake"])

    envio_id = fila_processamento.enfileirar_envio("cupom.jpg", b"bytes-da-foto", db_path=db_path, upload_dir=upload_dir)

    processou = ocr_worker.processar_proximo_envio(db_path=db_path)

    assert processou is True
    envio = storage_db.buscar_envio_por_id(envio_id, db_path=db_path)
    assert envio["status"] == "concluido"
    assert envio["nota_fiscal_id"] is not None

    nota = storage_db.buscar_nota_por_id(envio["nota_fiscal_id"], db_path=db_path)
    assert nota.chave_acesso == chave
    assert nota.status.value == "completa"


def test_processar_proximo_envio_falha_no_ocr_ainda_conclui_com_nota_minima(db_path, upload_dir, monkeypatch):
    def _levanta_erro(imagem):
        raise RuntimeError("Tesseract explodiu")

    monkeypatch.setattr("src.worker.ocr_worker.ocr_client.reconhecer_texto_de_imagem", _levanta_erro)
    monkeypatch.setattr("src.worker.ocr_worker._imagens_do_envio", lambda envio: ["imagem-fake"])

    envio_id = fila_processamento.enfileirar_envio(
        "cupom_ilegivel.jpg", b"bytes-ilegiveis", db_path=db_path, upload_dir=upload_dir
    )

    processou = ocr_worker.processar_proximo_envio(db_path=db_path)

    assert processou is True
    envio = storage_db.buscar_envio_por_id(envio_id, db_path=db_path)
    assert envio["status"] == "concluido"
    assert envio["nota_fiscal_id"] is not None

    nota = storage_db.buscar_nota_por_id(envio["nota_fiscal_id"], db_path=db_path)
    assert nota.status.value == "pendente_revisao"
    assert nota.chave_acesso is None
    assert nota.hash_conteudo is not None


def test_processar_proximo_envio_prioriza_qrcode_sobre_ocr_de_texto(db_path, upload_dir, monkeypatch):
    """QR Code tem correcao de erro embutida e e tentado antes do OCR de
    texto completo; quando decodifica, reaproveita a mesma orquestracao
    do canal URL/chave (inclusive a busca best-effort na SEFAZ)."""
    import qrcode as qrcode_lib

    from src.services.sefaz_client import DadosNotaSefaz
    from tests.helpers import gerar_chave_valida

    chave = gerar_chave_valida(numero="000000900")
    url = f"https://www.sefaz.sp.gov.br/nfce/qrcode?p={chave}|2|1|1|hash"
    imagem_qrcode = qrcode_lib.make(url).convert("RGB")

    monkeypatch.setattr("src.worker.ocr_worker._imagens_do_envio", lambda envio: [imagem_qrcode])
    monkeypatch.setattr(
        "src.worker.ocr_worker.ocr_client.reconhecer_texto_de_imagem",
        lambda imagem: (_ for _ in ()).throw(AssertionError("OCR de texto nao deveria ter sido chamado")),
    )
    monkeypatch.setattr(
        "src.services.importador.sefaz_client.buscar_dados_nota",
        lambda url: DadosNotaSefaz(
            emitente_nome="Loja Via QR Code",
            data_emissao="2026-06-01",
            valor_total=5000,
            itens=[{"codigo_item": "1", "descricao": "Item", "quantidade": 1.0, "valor_unitario": 5000, "valor_total_item": 5000}],
        ),
    )

    envio_id = fila_processamento.enfileirar_envio("cupom.jpg", b"bytes-da-foto", db_path=db_path, upload_dir=upload_dir)

    processou = ocr_worker.processar_proximo_envio(db_path=db_path)

    assert processou is True
    envio = storage_db.buscar_envio_por_id(envio_id, db_path=db_path)
    nota = storage_db.buscar_nota_por_id(envio["nota_fiscal_id"], db_path=db_path)
    assert nota.chave_acesso == chave
    assert nota.canal_origem.value == "foto_pdf"
    assert nota.status.value == "completa"
    assert nota.emitente_nome == "Loja Via QR Code"


def test_processar_proximo_envio_qrcode_ausente_cai_para_ocr_de_texto(db_path, upload_dir, monkeypatch):
    """Sem QR Code decodificavel na imagem, o worker cai para o
    reconhecimento de texto completo (fallback, research.md #9)."""
    from tests.helpers import gerar_chave_valida

    chave = gerar_chave_valida(numero="000000901")
    texto_ocr = f"LOJA SEM QRCODE\n{chave}\n"

    monkeypatch.setattr("src.worker.ocr_worker._imagens_do_envio", lambda envio: ["imagem-sem-qrcode"])
    monkeypatch.setattr("src.worker.ocr_worker.ocr_client.reconhecer_texto_de_imagem", lambda imagem: texto_ocr)

    envio_id = fila_processamento.enfileirar_envio("cupom.jpg", b"bytes-da-foto", db_path=db_path, upload_dir=upload_dir)
    processou = ocr_worker.processar_proximo_envio(db_path=db_path)

    assert processou is True
    envio = storage_db.buscar_envio_por_id(envio_id, db_path=db_path)
    nota = storage_db.buscar_nota_por_id(envio["nota_fiscal_id"], db_path=db_path)
    assert nota.chave_acesso == chave
