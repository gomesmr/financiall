from __future__ import annotations

import openpyxl
import pytest

from src.scripts.seed_regras_natureza import seed_regras_natureza
from src.scripts.seed_taxonomia_categorizacao import seed_taxonomia
from src.services.importar_extrato_bb import parsear
from src.services.importar_historico_extrato import processar_transacoes
from src.storage import db as storage_db


@pytest.fixture()
def db_path(tmp_path):
    caminho = str(tmp_path / "financiall.db")
    storage_db.init_db(caminho)
    seed_taxonomia(db_path=caminho)
    seed_regras_natureza(db_path=caminho)
    return caminho


def _criar_extrato_bb(tmp_path, nome_arquivo, linhas):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Extrato Conta"
    ws.append(["Data", "Lançamento", "Detalhes", "N° documento", "Valor", "Tipo Lançamento"])
    for linha in linhas:
        ws.append(linha)
    caminho = tmp_path / nome_arquivo
    wb.save(str(caminho))
    return str(caminho)


_LINHAS_JANEIRO = [
    ["31/12/2025", "Saldo Anterior", " ", " ", "-500,00", " "],
    ["02/01/2026", "Contr BB Credito Salario", "", "100021000188775", "2.500,00", "Entrada"],
    ["02/01/2026", "Pix - Enviado", "02/01 13:50 INSTITUTO CG CLIN ODONTOL", "10201", "-300,00", "Saída"],
    ["06/01/2026", "Pix - Enviado", "06/01 12:49 MARCELO RENATO GOMES", "10601", "-600,00", "Saída"],
    ["00/00/0000", "Saldo do dia", " ", " ", "0,00", " "],
]


def test_parsear_e_processar_importa_transacoes_reais_da_cristine(tmp_path, db_path):
    caminho = _criar_extrato_bb(tmp_path, "Extrato conta corrente - 012026.xlsx", _LINHAS_JANEIRO)

    registros = parsear(caminho)
    resumo = processar_transacoes(registros, db_path=db_path)

    assert resumo.importadas == 3  # as duas linhas de saldo sao ignoradas
    assert resumo.puladas == 0

    conn = storage_db.get_connection(db_path)
    try:
        titulares = {row["titular"] for row in conn.execute("SELECT titular FROM transacao").fetchall()}
        contas = {row["conta"] for row in conn.execute("SELECT conta FROM transacao").fetchall()}
    finally:
        conn.close()
    assert titulares == {"cristine"}
    assert contas == {"bb_cristine_cc"}


def test_reimportar_o_mesmo_arquivo_nao_duplica(tmp_path, db_path):
    caminho = _criar_extrato_bb(tmp_path, "Extrato conta corrente - 012026.xlsx", _LINHAS_JANEIRO)

    registros = parsear(caminho)
    resumo1 = processar_transacoes(registros, db_path=db_path)
    resumo2 = processar_transacoes(registros, db_path=db_path)

    assert resumo1.importadas == 3
    assert resumo2.importadas == 0
    assert resumo2.ja_existentes == 3

    conn = storage_db.get_connection(db_path)
    total = conn.execute("SELECT COUNT(*) FROM transacao").fetchone()[0]
    conn.close()
    assert total == 3


def test_arquivo_novo_com_sobreposicao_parcial_so_importa_o_delta(tmp_path, db_path):
    """US3 (feature 011): simula o cenario real observado nos 5 arquivos
    reais (042026.xlsx e 042026_01.xlsx, uma reexportacao corrigida que
    cobre o mesmo periodo parcialmente) -- um segundo arquivo com 2
    transacoes repetidas e 1 nova so deve importar a nova."""
    caminho_mes1 = _criar_extrato_bb(tmp_path, "Extrato conta corrente - 012026.xlsx", _LINHAS_JANEIRO)
    resumo_mes1 = processar_transacoes(parsear(caminho_mes1), db_path=db_path)
    assert resumo_mes1.importadas == 3

    linhas_reexportacao = _LINHAS_JANEIRO + [
        ["07/01/2026", "Pix - Enviado", "07/01 10:00 NOVO ESTABELECIMENTO", "10701", "-45,00", "Saída"],
    ]
    caminho_mes1_reexportado = _criar_extrato_bb(
        tmp_path, "Extrato conta corrente - 012026_01.xlsx", linhas_reexportacao
    )
    resumo_reexportado = processar_transacoes(parsear(caminho_mes1_reexportado), db_path=db_path)

    assert resumo_reexportado.importadas == 1
    assert resumo_reexportado.ja_existentes == 3

    conn = storage_db.get_connection(db_path)
    total = conn.execute("SELECT COUNT(*) FROM transacao").fetchone()[0]
    conn.close()
    assert total == 4
