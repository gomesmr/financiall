from __future__ import annotations

import pytest

from src.models.nota_fiscal import CanalOrigem, NotaFiscal, StatusNota
from src.storage import db as storage_db
from tests.helpers import gerar_chave_valida


@pytest.fixture()
def db_path(tmp_path):
    caminho = str(tmp_path / "financiall.db")
    storage_db.init_db(caminho)
    return caminho


def _inserir_nota(db_path) -> int:
    nota = NotaFiscal(
        canal_origem=CanalOrigem.URL_CHAVE,
        status=StatusNota.COMPLETA,
        chave_acesso=gerar_chave_valida(),
    )
    return storage_db.inserir_nota(nota, db_path=db_path)


def test_atribuir_titular_a_nota(db_path):
    nota_id = _inserir_nota(db_path)

    resultado = storage_db.atribuir_titular_a_nota(nota_id, "marcelo", db_path=db_path)

    assert resultado is True
    nota = storage_db.buscar_nota_por_id(nota_id, db_path=db_path)
    assert nota.titular == "marcelo"


def test_trocar_titular_de_uma_nota(db_path):
    nota_id = _inserir_nota(db_path)
    storage_db.atribuir_titular_a_nota(nota_id, "marcelo", db_path=db_path)

    storage_db.atribuir_titular_a_nota(nota_id, "cristine", db_path=db_path)

    nota = storage_db.buscar_nota_por_id(nota_id, db_path=db_path)
    assert nota.titular == "cristine"


def test_remover_titular_de_uma_nota(db_path):
    nota_id = _inserir_nota(db_path)
    storage_db.atribuir_titular_a_nota(nota_id, "marcelo", db_path=db_path)

    storage_db.atribuir_titular_a_nota(nota_id, None, db_path=db_path)

    nota = storage_db.buscar_nota_por_id(nota_id, db_path=db_path)
    assert nota.titular is None


def test_atribuir_titular_a_nota_inexistente_retorna_none(db_path):
    resultado = storage_db.atribuir_titular_a_nota(999, "marcelo", db_path=db_path)
    assert resultado is None


def test_atribuir_titular_invalido_retorna_false(db_path):
    nota_id = _inserir_nota(db_path)
    resultado = storage_db.atribuir_titular_a_nota(nota_id, "vizinho", db_path=db_path)
    assert resultado is False
