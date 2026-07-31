from __future__ import annotations

import openpyxl
import pytest
import xlwt

from src.services.importar_extrato_upload import FormatoNaoReconhecidoError, detectar_e_parsear


def _criar_xls(caminho, linhas):
    workbook = xlwt.Workbook()
    planilha = workbook.add_sheet("Planilha")
    for indice_linha, linha in enumerate(linhas):
        for indice_coluna, valor in enumerate(linha):
            planilha.write(indice_linha, indice_coluna, valor)
    workbook.save(str(caminho))


def _criar_xlsx(caminho, linhas):
    workbook = openpyxl.Workbook()
    planilha = workbook.active
    for linha in linhas:
        planilha.append(linha)
    workbook.save(str(caminho))


_LINHAS_ITAU_FATURA_XLS = [
    ["Data", "Lançamento", "Tipo", "Valor"],
    ["10/06/2026", "SJX COMERCIAL", "", 150.50],
]

_LINHAS_ITAU_EXTRATO_CC_XLS = [
    ["data", "lançamento", "ag./origem", "valor (R$)", "saldos (R$)"],
    ["31/05/2026", "SALDO ANTERIOR", "", "", 3529.88],
    ["01/06/2026", "INT ITAU MULT", "", -583.17, ""],
]

_LINHAS_ITAU_FATURA_XLSX = [
    [None, None],
    [None, "Nome", "Marcelo Renato Gomes"],
    [None, "Fatura Paga - Junho/2026"],
    [None, "Data", "Lançamento", "Parcelamento", "Valor", None, "Titularidade"],
]

_LINHAS_BB_EXTRATO_XLSX = [
    ["Data", "Lançamento", "Detalhes", "N° documento", "Valor", "Tipo Lançamento"],
    ["02/01/2026", "Contr BB Credito Salario", "", "100021000188775", "2.500,00", "Entrada"],
]


def test_detecta_fatura_itau_xls(tmp_path):
    caminho = tmp_path / "fatura.xls"
    _criar_xls(caminho, _LINHAS_ITAU_FATURA_XLS)
    formato, registros = detectar_e_parsear(str(caminho), "fatura.xls")
    assert formato == "itau_fatura_cartao"
    assert len(registros) == 1


def test_detecta_extrato_cc_itau_xls(tmp_path):
    caminho = tmp_path / "extrato.xls"
    _criar_xls(caminho, _LINHAS_ITAU_EXTRATO_CC_XLS)
    formato, registros = detectar_e_parsear(str(caminho), "extrato.xls")
    assert formato == "itau_extrato_cc"
    assert len(registros) == 1


def test_detecta_fatura_itau_xlsx(tmp_path):
    caminho = tmp_path / "fatura.xlsx"
    _criar_xlsx(caminho, _LINHAS_ITAU_FATURA_XLSX)
    formato, registros = detectar_e_parsear(str(caminho), "fatura.xlsx")
    assert formato == "itau_fatura_cartao"
    assert registros == []  # sem linha de lancamento valida na fixture minima -- so testa deteccao


def test_detecta_extrato_bb_xlsx(tmp_path):
    caminho = tmp_path / "extrato.xlsx"
    _criar_xlsx(caminho, _LINHAS_BB_EXTRATO_XLSX)
    formato, registros = detectar_e_parsear(str(caminho), "extrato.xlsx")
    assert formato == "bb_extrato_cc"
    assert len(registros) == 1


def test_detecta_fatura_mercado_pago_pdf_por_extensao(tmp_path, monkeypatch):
    sentinela = [{"descricao": "teste"}]
    monkeypatch.setattr(
        "src.services.importar_extrato_upload.importar_fatura_mercado_pago.parsear",
        lambda caminho: sentinela,
    )
    formato, registros = detectar_e_parsear("qualquer-caminho.pdf", "fatura.pdf")
    assert formato == "mercado_pago_fatura"
    assert registros is sentinela


def test_extensao_nao_suportada_levanta_erro(tmp_path):
    caminho = tmp_path / "documento.docx"
    caminho.write_text("conteudo qualquer")
    with pytest.raises(FormatoNaoReconhecidoError):
        detectar_e_parsear(str(caminho), "documento.docx")


def test_xls_sem_assinatura_reconhecivel_levanta_erro(tmp_path):
    caminho = tmp_path / "generico.xls"
    _criar_xls(caminho, [["coluna a", "coluna b"], ["x", "y"]])
    with pytest.raises(FormatoNaoReconhecidoError):
        detectar_e_parsear(str(caminho), "generico.xls")


def test_xlsx_sem_assinatura_reconhecivel_levanta_erro(tmp_path):
    caminho = tmp_path / "generico.xlsx"
    _criar_xlsx(caminho, [["coluna a", "coluna b"], ["x", "y"]])
    with pytest.raises(FormatoNaoReconhecidoError):
        detectar_e_parsear(str(caminho), "generico.xlsx")
