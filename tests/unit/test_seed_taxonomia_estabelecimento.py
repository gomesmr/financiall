from __future__ import annotations

import pytest

from src.scripts import seed_taxonomia_estabelecimento as seed
from src.storage import db as storage_db


@pytest.fixture()
def db_path(tmp_path):
    caminho = str(tmp_path / "financiall.db")
    storage_db.init_db(caminho)
    return caminho


def test_seed_cria_categorias_de_estabelecimento_esperadas(db_path):
    seed.seed_taxonomia_estabelecimento(db_path=db_path)

    categorias = storage_db.listar_categorias(db_path=db_path)
    por_nome = {c.nome: c for c in categorias}

    assert "Supermercado" in por_nome
    assert "Mercearia" in por_nome
    assert "Restaurante" in por_nome
    assert "Bar" in por_nome
    assert "Farmácia" in por_nome
    assert "Pet Shop" in por_nome
    assert "Saúde" in por_nome
    assert por_nome["Saúde"].parent_id is None
    assert "Dentista" in por_nome
    assert por_nome["Dentista"].parent_id == por_nome["Saúde"].id
    assert "Plano de Saúde" in por_nome
    assert por_nome["Plano de Saúde"].parent_id == por_nome["Saúde"].id


def test_seed_e_idempotente_rodar_duas_vezes_nao_duplica(db_path):
    seed.seed_taxonomia_estabelecimento(db_path=db_path)
    seed.seed_taxonomia_estabelecimento(db_path=db_path)

    categorias = storage_db.listar_categorias(db_path=db_path)
    nomes = [c.nome for c in categorias]

    assert nomes.count("Supermercado") == 1
    assert nomes.count("Saúde") == 1
    assert nomes.count("Dentista") == 1


def test_seed_preserva_categoria_de_estabelecimento_ja_criada_pelo_usuario(db_path):
    categoria_existente_id = storage_db.criar_categoria("Supermercado", db_path=db_path)

    seed.seed_taxonomia_estabelecimento(db_path=db_path)

    categorias = storage_db.listar_categorias(db_path=db_path)
    supermercados = [c for c in categorias if c.nome == "Supermercado"]
    assert len(supermercados) == 1
    assert supermercados[0].id == categoria_existente_id
