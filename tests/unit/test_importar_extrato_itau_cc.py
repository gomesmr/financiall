from __future__ import annotations

from src.services.importar_extrato_itau_cc import parsear


def _criar_extrato_cc_xls(caminho, linhas: list[list], nome_arquivo="Extrato Conta Corrente-220720261133.xls"):
    import xlwt

    workbook = xlwt.Workbook()
    planilha = workbook.add_sheet("Extrato")
    for indice_linha, linha in enumerate(linhas):
        for indice_coluna, valor in enumerate(linha):
            planilha.write(indice_linha, indice_coluna, valor)
    destino = caminho / nome_arquivo
    workbook.save(str(destino))
    return str(destino)


_LINHAS_CC_SINTETICA = [
    ["data", "lançamento", "ag./origem", "valor (R$)", "saldos (R$)"],
    ["31/05/2026", "SALDO ANTERIOR", "", "", 3529.88],
    ["01/06/2026", "INT ITAU MULT", "", -583.17, ""],
    ["01/06/2026", "CREDIARIO AUTOM 18/20", "", -800.66, ""],
    ["01/06/2026", "SALDO TOTAL DISPONÍVEL DIA", "", "", 319.32],
    ["25/06/2026", "PAGTO REMUNERACAO", "", 5717.68, ""],
]


def test_parsear_ignora_linhas_de_saldo(tmp_path):
    caminho = _criar_extrato_cc_xls(tmp_path, _LINHAS_CC_SINTETICA)

    registros = parsear(caminho)

    descricoes = [r["descricao"] for r in registros]
    assert descricoes == ["INT ITAU MULT", "CREDIARIO AUTOM 18/20", "PAGTO REMUNERACAO"]


def test_parsear_preserva_data_iso_e_valor_com_sinal(tmp_path):
    caminho = _criar_extrato_cc_xls(tmp_path, _LINHAS_CC_SINTETICA)

    registros = parsear(caminho)
    saida = next(r for r in registros if r["descricao"] == "INT ITAU MULT")
    entrada = next(r for r in registros if r["descricao"] == "PAGTO REMUNERACAO")

    assert saida["data"] == "2026-06-01"
    assert saida["valor_raw"] == -583.17
    assert entrada["valor_raw"] == 5717.68


def test_parsear_conta_e_titular_fixos(tmp_path):
    caminho = _criar_extrato_cc_xls(tmp_path, _LINHAS_CC_SINTETICA)
    registros = parsear(caminho)
    assert all(r["conta"] == "Itaú_CC" for r in registros)
    assert all(r["titular"] == "marcelo" for r in registros)


def test_parsear_registra_fonte_como_nome_do_arquivo(tmp_path):
    caminho = _criar_extrato_cc_xls(tmp_path, _LINHAS_CC_SINTETICA)
    registros = parsear(caminho)
    assert all(r["fonte"] == "Extrato Conta Corrente-220720261133.xls" for r in registros)


def test_parsear_arquivo_vazio_retorna_lista_vazia(tmp_path):
    caminho = _criar_extrato_cc_xls(tmp_path, [["data", "lançamento", "ag./origem", "valor (R$)", "saldos (R$)"]])
    assert parsear(caminho) == []


def test_parser_e_persistencia_compartilhada_classificam_e_nao_duplicam(tmp_path):
    from src.scripts.seed_regras_natureza import seed_regras_natureza
    from src.scripts.seed_taxonomia_categorizacao import seed_taxonomia
    from src.services.importar_historico_extrato import processar_transacoes
    from src.storage import db as storage_db

    db_path = str(tmp_path / "financiall.db")
    storage_db.init_db(db_path)
    seed_taxonomia(db_path=db_path)
    seed_regras_natureza(db_path=db_path)

    caminho = _criar_extrato_cc_xls(tmp_path, _LINHAS_CC_SINTETICA)
    registros = parsear(caminho)

    primeira = processar_transacoes(registros, db_path=db_path)
    segunda = processar_transacoes(registros, db_path=db_path)

    assert primeira.importadas == 3
    assert segunda.importadas == 0
    assert segunda.ja_existentes == 3
