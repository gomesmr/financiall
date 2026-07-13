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
    monkeypatch.setattr("src.worker.ocr_worker.ocr_client.reconhecer_texto", lambda caminho: texto_ocr)

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
    def _levanta_erro(caminho):
        raise RuntimeError("Tesseract explodiu")

    monkeypatch.setattr("src.worker.ocr_worker.ocr_client.reconhecer_texto", _levanta_erro)

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
