from __future__ import annotations

import pytest

from src.services import campos_ocr as campos_ocr_service
from src.services import importador
from src.services import sefaz_client
from src.storage import db as storage_db
from tests.helpers import gerar_chave_valida


@pytest.fixture()
def db_path(tmp_path):
    caminho = str(tmp_path / "financiall.db")
    storage_db.init_db(caminho)
    return caminho


# --- US3: nao duplicar --------------------------------------------------


def test_importar_por_chave_colada_duas_vezes_nao_duplica(db_path):
    chave = gerar_chave_valida()

    primeiro = importador.importar_por_url_ou_chave(chave, db_path=db_path)
    segundo = importador.importar_por_url_ou_chave(chave, db_path=db_path)

    assert primeiro.status != "ja_registrada"
    assert segundo.status == "ja_registrada"
    assert len(storage_db.listar_notas(db_path=db_path)) == 1


def test_importar_por_ocr_duas_vezes_com_mesmo_hash_nao_duplica(db_path):
    campos = campos_ocr_service.CamposExtraidos()  # nenhuma chave identificada
    hash_conteudo = "hash-fixo-do-arquivo"

    primeiro = importador.importar_por_ocr(campos, hash_conteudo, db_path=db_path)
    segundo = importador.importar_por_ocr(campos, hash_conteudo, db_path=db_path)

    assert primeiro.status != "ja_registrada"
    assert segundo.status == "ja_registrada"
    assert len(storage_db.listar_notas(db_path=db_path)) == 1


def test_importar_mesma_chave_via_url_depois_via_ocr_nao_duplica(db_path, monkeypatch):
    chave = gerar_chave_valida()
    monkeypatch.setattr(
        "src.services.importador.sefaz_client.buscar_dados_nota",
        lambda url: sefaz_client.DadosNotaSefaz(),
    )
    url = f"https://www.sefaz.sp.gov.br/nfce/qrcode?p={chave}|2|1|1|hash"

    resultado_url = importador.importar_por_url_ou_chave(url, db_path=db_path)

    campos_ocr_com_a_mesma_chave = campos_ocr_service.CamposExtraidos(chave_acesso=chave)
    resultado_ocr = importador.importar_por_ocr(
        campos_ocr_com_a_mesma_chave, "hash-completamente-diferente", db_path=db_path
    )

    assert resultado_url.status != "ja_registrada"
    assert resultado_ocr.status == "ja_registrada"
    assert resultado_ocr.nota.chave_acesso == chave
    assert len(storage_db.listar_notas(db_path=db_path)) == 1


# --- US4: degradacao graciosa -------------------------------------------


def test_importar_por_url_com_sefaz_indisponivel_fica_pendente_revisao(db_path, monkeypatch):
    def _levanta_indisponivel(url):
        raise sefaz_client.BuscaSefazIndisponivelError("timeout simulado")

    monkeypatch.setattr("src.services.importador.sefaz_client.buscar_dados_nota", _levanta_indisponivel)

    chave = gerar_chave_valida()
    url = f"https://www.sefaz.sp.gov.br/nfce/qrcode?p={chave}|2|1|1|hash"

    resultado = importador.importar_por_url_ou_chave(url, db_path=db_path)

    assert resultado.status == "pendente_revisao"
    assert resultado.nota.uf is not None  # decodificado da propria chave, independente da SEFAZ
    assert resultado.nota.chave_acesso == chave


def test_importar_por_chave_colada_sem_url_nunca_tenta_sefaz_e_fica_pendente(db_path):
    chave = gerar_chave_valida()
    resultado = importador.importar_por_url_ou_chave(chave, db_path=db_path)
    assert resultado.status == "pendente_revisao"


def test_importar_por_ocr_sem_nenhum_campo_ainda_grava_nota_minima(db_path):
    campos_vazios = campos_ocr_service.CamposExtraidos()
    resultado = importador.importar_por_ocr(campos_vazios, "hash-de-foto-ilegivel", db_path=db_path)

    assert resultado.status == "pendente_revisao"
    assert resultado.nota.hash_conteudo == "hash-de-foto-ilegivel"
    assert resultado.nota.chave_acesso is None
