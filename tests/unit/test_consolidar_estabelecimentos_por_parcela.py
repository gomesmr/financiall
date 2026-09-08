from __future__ import annotations

import sqlite3

import pytest

from src.scripts.consolidar_estabelecimentos_por_parcela import consolidar
from src.storage import db as storage_db


@pytest.fixture()
def db_path(tmp_path):
    caminho = str(tmp_path / "financiall.db")
    storage_db.init_db(caminho)
    return caminho


def _inserir_estabelecimento(db_path, eid, descricao_normalizada, nome_fantasia=None, tipo_categoria_id=None):
    con = sqlite3.connect(db_path)
    con.execute(
        "INSERT INTO estabelecimento (id, descricao_normalizada, nome_fantasia, tipo_categoria_id) VALUES (?, ?, ?, ?)",
        (eid, descricao_normalizada, nome_fantasia, tipo_categoria_id),
    )
    con.execute(
        "INSERT INTO transacao (fingerprint, data, descricao, valor, tipo, conta, natureza, estabelecimento_id, data_importacao) "
        "VALUES (?, '2026-01-01', 'x', 100, 'saida', 'itau_2486', 'gasto', ?, '2026-01-01')",
        (f"fp-{eid}", eid),
    )
    con.commit()
    con.close()


def test_funde_grupo_com_forma_canonica_e_sufixada(db_path):
    """Regressao: quando o grupo tem um membro JA na forma canonica (sem
    sufixo) e o sobrevivente escolhido e outro (por ja ter nome_fantasia),
    renomear o sobrevivente pra chave canonica colidia com o indice unico
    parcial antes do membro bare ser apagado (achado rodando contra o
    banco de producao real)."""
    _inserir_estabelecimento(db_path, 20, "CLARICELL")
    _inserir_estabelecimento(db_path, 21, "CLARICELL PARCELA 12 DE 21", nome_fantasia="Claro", tipo_categoria_id=81)

    resultado = consolidar(db_path)

    assert resultado == {"grupos_afetados": 1, "estabelecimentos_fundidos": 1}
    con = sqlite3.connect(db_path)
    linhas = con.execute("SELECT id, descricao_normalizada, nome_fantasia FROM estabelecimento").fetchall()
    assert linhas == [(21, "CLARICELL", "Claro")]


def test_funde_multiplas_parcelas_escolhendo_nomeado_como_sobrevivente(db_path):
    _inserir_estabelecimento(db_path, 10, "CLARICELL 09/21")
    _inserir_estabelecimento(db_path, 11, "CLARICELL PARCELA 12 DE 21", nome_fantasia="Claro", tipo_categoria_id=81)
    _inserir_estabelecimento(db_path, 12, "CLARICELL 15/21")
    _inserir_estabelecimento(db_path, 13, "OUTRA LOJA")

    resultado = consolidar(db_path)

    assert resultado == {"grupos_afetados": 1, "estabelecimentos_fundidos": 2}
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    restantes = {r["id"]: r["descricao_normalizada"] for r in con.execute("SELECT id, descricao_normalizada FROM estabelecimento")}
    assert restantes == {11: "CLARICELL", 13: "OUTRA LOJA"}
    transacoes = {r[0]: r[1] for r in con.execute("SELECT fingerprint, estabelecimento_id FROM transacao")}
    assert transacoes == {"fp-10": 11, "fp-11": 11, "fp-12": 11, "fp-13": 13}


def test_normaliza_estabelecimento_sozinho_sem_precisar_de_grupo(db_path):
    """Nao ha duplicata pra fundir, mas a descricao_normalizada armazenada
    ainda tem o sufixo de parcela -- deve ser normalizada mesmo assim."""
    _inserir_estabelecimento(db_path, 30, "NATURA PAY PARCELA 1 DE 10")

    resultado = consolidar(db_path)

    assert resultado == {"grupos_afetados": 0, "estabelecimentos_fundidos": 0}
    con = sqlite3.connect(db_path)
    assert con.execute("SELECT descricao_normalizada FROM estabelecimento WHERE id = 30").fetchone()[0] == "NATURA PAY"


def test_idempotente_segunda_passada_nao_faz_nada(db_path):
    _inserir_estabelecimento(db_path, 10, "CLARICELL 09/21")
    _inserir_estabelecimento(db_path, 11, "CLARICELL PARCELA 12 DE 21")

    consolidar(db_path)
    resultado_segunda_passada = consolidar(db_path)

    assert resultado_segunda_passada == {"grupos_afetados": 0, "estabelecimentos_fundidos": 0}
