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


# --- US1: criar categoria -------------------------------------------------


def test_criar_categoria_nome_valido_retorna_id(db_path):
    categoria_id = storage_db.criar_categoria("Alimentação", db_path=db_path)
    assert isinstance(categoria_id, int)
    categoria = storage_db.buscar_categoria_por_id(categoria_id, db_path=db_path)
    assert categoria.nome == "Alimentação"


def test_criar_categoria_nome_vazio_retorna_none(db_path):
    assert storage_db.criar_categoria("", db_path=db_path) is None
    assert storage_db.criar_categoria("   ", db_path=db_path) is None


@pytest.mark.parametrize(
    "primeiro,segundo",
    [
        ("Alimentação", "Alimentação"),
        ("Alimentação", "alimentação"),
        ("Alimentação", "  Alimentação  "),
        ("Transporte", "TRANSPORTE"),
    ],
)
def test_criar_categoria_nome_duplicado_retorna_none(db_path, primeiro, segundo):
    assert storage_db.criar_categoria(primeiro, db_path=db_path) is not None
    assert storage_db.criar_categoria(segundo, db_path=db_path) is None
    assert len(storage_db.listar_categorias(db_path=db_path)) == 1


# --- US2: atribuir categoria a uma nota -----------------------------------


def test_atribuir_categoria_a_nota(db_path):
    nota_id = _inserir_nota(db_path)
    categoria_id = storage_db.criar_categoria("Transporte", db_path=db_path)

    resultado = storage_db.atribuir_categoria_a_nota(nota_id, categoria_id, db_path=db_path)

    assert resultado is True
    nota = storage_db.buscar_nota_por_id(nota_id, db_path=db_path)
    assert nota.categoria_id == categoria_id


def test_trocar_categoria_de_uma_nota(db_path):
    nota_id = _inserir_nota(db_path)
    categoria_1 = storage_db.criar_categoria("Transporte", db_path=db_path)
    categoria_2 = storage_db.criar_categoria("Saúde", db_path=db_path)
    storage_db.atribuir_categoria_a_nota(nota_id, categoria_1, db_path=db_path)

    storage_db.atribuir_categoria_a_nota(nota_id, categoria_2, db_path=db_path)

    nota = storage_db.buscar_nota_por_id(nota_id, db_path=db_path)
    assert nota.categoria_id == categoria_2


def test_remover_categoria_de_uma_nota(db_path):
    nota_id = _inserir_nota(db_path)
    categoria_id = storage_db.criar_categoria("Transporte", db_path=db_path)
    storage_db.atribuir_categoria_a_nota(nota_id, categoria_id, db_path=db_path)

    storage_db.atribuir_categoria_a_nota(nota_id, None, db_path=db_path)

    nota = storage_db.buscar_nota_por_id(nota_id, db_path=db_path)
    assert nota.categoria_id is None


def test_atribuir_categoria_a_nota_inexistente_retorna_none(db_path):
    categoria_id = storage_db.criar_categoria("Transporte", db_path=db_path)
    resultado = storage_db.atribuir_categoria_a_nota(999, categoria_id, db_path=db_path)
    assert resultado is None


def test_atribuir_categoria_inexistente_retorna_false(db_path):
    nota_id = _inserir_nota(db_path)
    resultado = storage_db.atribuir_categoria_a_nota(nota_id, 999, db_path=db_path)
    assert resultado is False


# --- US4: editar categoria -------------------------------------------------


def test_editar_categoria_nome_valido_atualiza(db_path):
    categoria_id = storage_db.criar_categoria("Transporte", db_path=db_path)

    resultado = storage_db.editar_categoria(categoria_id, "Transportes", db_path=db_path)

    assert resultado is True
    categoria = storage_db.buscar_categoria_por_id(categoria_id, db_path=db_path)
    assert categoria.nome == "Transportes"


def test_editar_categoria_inexistente_retorna_none(db_path):
    resultado = storage_db.editar_categoria(999, "Novo Nome", db_path=db_path)
    assert resultado is None


def test_editar_categoria_para_nome_duplicado_retorna_false(db_path):
    storage_db.criar_categoria("Transporte", db_path=db_path)
    categoria_2 = storage_db.criar_categoria("Saúde", db_path=db_path)

    resultado = storage_db.editar_categoria(categoria_2, "transporte", db_path=db_path)

    assert resultado is False
    categoria = storage_db.buscar_categoria_por_id(categoria_2, db_path=db_path)
    assert categoria.nome == "Saúde"


# --- US5: excluir categoria -------------------------------------------------


def test_excluir_categoria_sem_notas(db_path):
    categoria_id = storage_db.criar_categoria("Lazer", db_path=db_path)

    resultado = storage_db.excluir_categoria(categoria_id, db_path=db_path)

    assert resultado is True
    assert storage_db.buscar_categoria_por_id(categoria_id, db_path=db_path) is None


def test_excluir_categoria_com_notas_desassocia(db_path):
    nota_id = _inserir_nota(db_path)
    categoria_id = storage_db.criar_categoria("Lazer", db_path=db_path)
    storage_db.atribuir_categoria_a_nota(nota_id, categoria_id, db_path=db_path)

    resultado = storage_db.excluir_categoria(categoria_id, db_path=db_path)

    assert resultado is True
    nota = storage_db.buscar_nota_por_id(nota_id, db_path=db_path)
    assert nota.categoria_id is None


def test_excluir_categoria_inexistente_retorna_false(db_path):
    resultado = storage_db.excluir_categoria(999, db_path=db_path)
    assert resultado is False
