from __future__ import annotations

import pytest

from src.scripts.seed_taxonomia_categorizacao import seed_taxonomia
from src.scripts.seed_regras_natureza import seed_regras_natureza
from src.services import classificacao_natureza
from src.storage import db as storage_db


@pytest.fixture()
def db_path(tmp_path):
    caminho = str(tmp_path / "financiall.db")
    storage_db.init_db(caminho)
    return caminho


# --- classificar_natureza: cascata cache -> regra -> pendente --------------


def test_classificar_natureza_resolve_via_cache(db_path):
    conn = storage_db.get_connection(db_path)
    conn.execute(
        "INSERT INTO cache_descricao_natureza (descricao_normalizada, natureza, categoria_id) VALUES (?, ?, ?)",
        ("PAGTO SALARIO EMPRESA X", "renda", None),
    )
    conn.commit()
    conn.close()

    natureza, categoria_id, metodo = classificacao_natureza.classificar_natureza(
        "Pagto Salario Empresa X", db_path=db_path
    )

    assert natureza == "renda"
    assert categoria_id is None
    assert metodo == "cache"


def test_classificar_natureza_resolve_via_regra_quando_sem_cache(db_path):
    categoria_id = storage_db.criar_categoria("Transporte", db_path=db_path)
    conn = storage_db.get_connection(db_path)
    conn.execute(
        "INSERT INTO regra_natureza (padrao, natureza, categoria_id, prioridade, ativa) VALUES (?, ?, ?, 10, 1)",
        ("UBER", "gasto", categoria_id),
    )
    conn.commit()
    conn.close()

    natureza, categoria_id_resultado, metodo = classificacao_natureza.classificar_natureza(
        "UBER *TRIP SAO PAULO", db_path=db_path
    )

    assert natureza == "gasto"
    assert categoria_id_resultado == categoria_id
    assert metodo == "regra"


def test_classificar_natureza_regra_inativa_nao_e_usada(db_path):
    conn = storage_db.get_connection(db_path)
    conn.execute(
        "INSERT INTO regra_natureza (padrao, natureza, categoria_id, prioridade, ativa) VALUES (?, ?, NULL, 10, 0)",
        ("UBER", "gasto"),
    )
    conn.commit()
    conn.close()

    resultado = classificacao_natureza.classificar_natureza("UBER *TRIP", db_path=db_path)
    assert resultado == (None, None, None)


def test_classificar_natureza_sem_correspondencia_fica_pendente(db_path):
    resultado = classificacao_natureza.classificar_natureza("DESCRICAO NUNCA VISTA", db_path=db_path)
    assert resultado == (None, None, None)


@pytest.mark.parametrize("descricao", [None, "", "   "])
def test_classificar_natureza_descricao_vazia_fica_pendente_sem_excecao(db_path, descricao):
    resultado = classificacao_natureza.classificar_natureza(descricao, db_path=db_path)
    assert resultado == (None, None, None)


def test_classificar_natureza_regra_mais_especifica_prioridade_maior_vence(db_path):
    conn = storage_db.get_connection(db_path)
    conn.execute(
        "INSERT INTO regra_natureza (padrao, natureza, categoria_id, prioridade, ativa) VALUES (?, 'pagamento_fatura', NULL, 90, 1)",
        ("MERCADO PAG",),
    )
    conn.execute(
        "INSERT INTO regra_natureza (padrao, natureza, categoria_id, prioridade, ativa) VALUES (?, 'gasto', NULL, 70, 1)",
        ("MERCADOLIVRE",),
    )
    conn.commit()
    conn.close()

    natureza, _, metodo = classificacao_natureza.classificar_natureza(
        "PIX QRS MERCADO PAG LTDA", db_path=db_path
    )

    assert natureza == "pagamento_fatura"
    assert metodo == "regra"


# --- regras-semente reais migradas do script legado (research.md #5) -------


@pytest.fixture()
def db_com_regras_semente(tmp_path):
    caminho = str(tmp_path / "financiall.db")
    storage_db.init_db(caminho)
    seed_taxonomia(db_path=caminho)
    seed_regras_natureza(db_path=caminho)
    return caminho


@pytest.mark.parametrize(
    "descricao,natureza_esperada",
    [
        ("PAGTO SALARIO REF 07/2026", "renda"),
        ("TBI 0300.46235-5", "gasto"),
        ("FATURA PAGA", "pagamento_fatura"),
        ("PIX TRANSF CRISTINE GOMES", "transferencia_interna"),
        ("SJX COMERCIAL LTDA", "gasto"),
        ("UBER *TRIP", "gasto"),
        ("DROGASIL 123", "gasto"),
    ],
)
def test_regras_semente_reais_classificam_descricoes_conhecidas(db_com_regras_semente, descricao, natureza_esperada):
    natureza, _categoria_id, metodo = classificacao_natureza.classificar_natureza(
        descricao, db_path=db_com_regras_semente
    )
    assert natureza == natureza_esperada
    assert metodo == "regra"


def test_seed_regras_natureza_e_idempotente(db_com_regras_semente):
    conn = storage_db.get_connection(db_com_regras_semente)
    total_antes = conn.execute("SELECT COUNT(*) FROM regra_natureza").fetchone()[0]
    conn.close()

    inseridas_segunda_vez = seed_regras_natureza(db_path=db_com_regras_semente)

    conn = storage_db.get_connection(db_com_regras_semente)
    total_depois = conn.execute("SELECT COUNT(*) FROM regra_natureza").fetchone()[0]
    conn.close()

    assert inseridas_segunda_vez == 0
    assert total_depois == total_antes
