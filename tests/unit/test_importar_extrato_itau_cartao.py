from __future__ import annotations

from datetime import datetime

import openpyxl
import pytest

from src.services.importar_extrato_itau_cartao import parsear


def _criar_fatura_xls(caminho, linhas: list[list], nome_arquivo="cartao-2486-Fatura-Excel.xls"):
    import xlwt

    workbook = xlwt.Workbook()
    planilha = workbook.add_sheet("Fatura")
    for indice_linha, linha in enumerate(linhas):
        for indice_coluna, valor in enumerate(linha):
            planilha.write(indice_linha, indice_coluna, valor)
    destino = caminho / nome_arquivo
    workbook.save(str(destino))
    return str(destino)


_LINHAS_FATURA_SINTETICA = [
    ["Data", "Lançamento", "Tipo", "Valor"],  # cabecalho -- ignorado
    ["10/06/2026", "SJX COMERCIAL", "", 150.50],  # compra valida
    ["11/06/2026", "PAGAMENTO EFETUADO", "", -500.0],  # pagamento de fatura -- ignorado
    ["", "Total desta fatura", "", 300.0],  # linha de total -- ignorada
    ["12/06/2026", "FARMACIA TESTE", "", 45.00],  # compra valida
    ["13/06/2026", "ESTORNO COMPRA", "", -20.00],  # estorno/credito -- valida (valor negativo)
]


def test_parsear_ignora_cabecalho_total_e_pagamento_efetuado(tmp_path):
    caminho = _criar_fatura_xls(tmp_path, _LINHAS_FATURA_SINTETICA)

    registros = parsear(caminho)

    descricoes = [r["descricao"] for r in registros]
    assert descricoes == ["SJX COMERCIAL", "FARMACIA TESTE", "ESTORNO COMPRA"]


def test_parsear_preserva_data_iso_e_valor_com_sinal(tmp_path):
    caminho = _criar_fatura_xls(tmp_path, _LINHAS_FATURA_SINTETICA)

    registros = parsear(caminho)
    compra = next(r for r in registros if r["descricao"] == "SJX COMERCIAL")
    estorno = next(r for r in registros if r["descricao"] == "ESTORNO COMPRA")

    assert compra["data"] == "2026-06-10"
    assert compra["valor_raw"] == 150.50
    assert estorno["valor_raw"] == -20.00


def test_parsear_deriva_conta_pelo_nome_do_arquivo(tmp_path):
    caminho_2486 = _criar_fatura_xls(tmp_path, _LINHAS_FATURA_SINTETICA, nome_arquivo="cartao-2486-Fatura-Excel.xls")
    registros_2486 = parsear(caminho_2486)
    assert registros_2486[0]["conta"] == "Itaú_2486"

    caminho_9073 = _criar_fatura_xls(tmp_path, _LINHAS_FATURA_SINTETICA, nome_arquivo="cartao-9073-Fatura-Excel.xls")
    registros_9073 = parsear(caminho_9073)
    assert registros_9073[0]["conta"] == "Itaú_9073"


def test_parsear_registra_fonte_como_nome_do_arquivo(tmp_path):
    caminho = _criar_fatura_xls(tmp_path, _LINHAS_FATURA_SINTETICA)
    registros = parsear(caminho)
    assert all(r["fonte"] == "cartao-2486-Fatura-Excel.xls" for r in registros)


def test_parsear_arquivo_vazio_retorna_lista_vazia(tmp_path):
    caminho = _criar_fatura_xls(tmp_path, [["Data", "Lançamento", "Tipo", "Valor"]])
    assert parsear(caminho) == []


def test_parsear_marca_titular_como_marcelo(tmp_path):
    """feature 011: todo cartao Itau importado por este parser e do
    Marcelo -- achado na validacao com dado real (sem isso, nenhuma
    transacao historica dele tinha titular gravado)."""
    caminho = _criar_fatura_xls(tmp_path, _LINHAS_FATURA_SINTETICA)
    registros = parsear(caminho)
    assert all(r["titular"] == "marcelo" for r in registros)


# --- feature 011 US3: novo formato de fatura "Fatura Paga" (.xlsx) --------
# achado real: o Itau passou a exportar tambem nesse layout, com metadados
# no topo e colunas B=Data/C=Lancamento/D=Parcelamento/E=Valor/G=Titularidade.


def _criar_fatura_paga_xlsx(caminho, linhas_lancamento: list[list], nome_arquivo="fatura-paga-final 1035-junho2026.xlsx"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Fatura 06-26"
    ws.append([" "])
    ws.append([])
    ws.append([None, "Nome", "Marcelo Renato Gomes"])
    ws.append([None, "Agência", "0300"])
    ws.append([None, "Conta", "46235-5"])
    ws.append([])
    ws.append([None, "Fatura Paga - Junho/2026"])
    ws.append([None, "Cartão", None, None, None, None, "Valor"])
    ws.append([None, "Itau Multiplo Platinum Visa - final 1035", None, "Você pagou R$ 732,53 de  ", None, None, 732.53])
    ws.append([None, "Lançamentos"])
    ws.append([None, "Data", "Lançamento", "Parcelamento", "Valor", None, "Titularidade"])
    for linha in linhas_lancamento:
        ws.append([None] + linha)
    destino = caminho / nome_arquivo
    wb.save(str(destino))
    return str(destino)


_LINHAS_FATURA_PAGA_SINTETICA = [
    [datetime(2026, 6, 1), "Pagamento Efetuado", None, -583.17, None, "Titular"],
    [datetime(2026, 6, 20), "Amazon Servicos De Vare", None, 0.99, None, "Titular"],
    [datetime(2026, 6, 19), "Sjx - Comercial Atacad", None, 191.43, None, "Titular"],
    [None, None, "Subtotal ", None, None, None],
]


def test_parsear_fatura_paga_xlsx_ignora_metadados_e_pagamento_efetuado(tmp_path):
    caminho = _criar_fatura_paga_xlsx(tmp_path, _LINHAS_FATURA_PAGA_SINTETICA)

    registros = parsear(caminho)

    descricoes = [r["descricao"] for r in registros]
    assert descricoes == ["Amazon Servicos De Vare", "Sjx - Comercial Atacad"]


def test_parsear_fatura_paga_xlsx_preserva_data_iso_e_valor(tmp_path):
    caminho = _criar_fatura_paga_xlsx(tmp_path, _LINHAS_FATURA_PAGA_SINTETICA)

    registros = parsear(caminho)
    amazon = next(r for r in registros if r["descricao"] == "Amazon Servicos De Vare")

    assert amazon["data"] == "2026-06-20"
    assert amazon["valor_raw"] == 0.99


def test_parsear_fatura_paga_xlsx_deriva_conta_pelo_nome_do_arquivo(tmp_path):
    caminho = _criar_fatura_paga_xlsx(
        tmp_path, _LINHAS_FATURA_PAGA_SINTETICA, nome_arquivo="fatura-paga-final 2486-junho2026.xlsx"
    )
    registros = parsear(caminho)
    assert registros[0]["conta"] == "Itaú_2486"


def test_parsear_fatura_paga_xlsx_marca_titular_marcelo(tmp_path):
    caminho = _criar_fatura_paga_xlsx(tmp_path, _LINHAS_FATURA_PAGA_SINTETICA)
    registros = parsear(caminho)
    assert all(r["titular"] == "marcelo" for r in registros)


# --- integracao com processar_transacoes (reaproveita persistencia da US2) -


def test_parser_e_persistencia_compartilhada_classificam_e_nao_duplicam(tmp_path):
    from src.scripts.seed_regras_natureza import seed_regras_natureza
    from src.scripts.seed_taxonomia_categorizacao import seed_taxonomia
    from src.services.importar_historico_extrato import processar_transacoes
    from src.storage import db as storage_db

    db_path = str(tmp_path / "financiall.db")
    storage_db.init_db(db_path)
    seed_taxonomia(db_path=db_path)
    seed_regras_natureza(db_path=db_path)

    caminho = _criar_fatura_xls(tmp_path, _LINHAS_FATURA_SINTETICA)
    registros = parsear(caminho)

    primeira = processar_transacoes(registros, db_path=db_path)
    segunda = processar_transacoes(registros, db_path=db_path)

    assert primeira.importadas == 3
    assert segunda.importadas == 0
    assert segunda.ja_existentes == 3
