from __future__ import annotations

from src.services.campos_ocr import extrair_campos
from tests.helpers import gerar_chave_valida

CHAVE = gerar_chave_valida()

TEXTO_OCR_COMPLETO = f"""CUPOM FISCAL ELETRONICO SAT
FARMACIA EXEMPLO LTDA
CNPJ: 12.345.678/0001-99
Data emissao: 15/06/2026
DIPIRONA 500MG          1,000    12,50
AGUA MINERAL 500ML       2,000     6,00
VALOR TOTAL R$                   18,50
CHAVE DE ACESSO
{CHAVE}
"""

TEXTO_OCR_ILEGIVEL = "###   ...  borrado   ilegivel ---"


def test_extrair_campos_texto_completo_encontra_todos_os_campos():
    campos = extrair_campos(TEXTO_OCR_COMPLETO)
    assert campos.chave_acesso == CHAVE
    assert campos.emitente_nome == "FARMACIA EXEMPLO LTDA"
    assert campos.cnpj_emitente == "12345678000199"
    assert campos.data_emissao == "2026-06-15"
    assert campos.valor_total == 1850
    assert len(campos.itens) == 2
    assert campos.itens[0]["descricao"] == "DIPIRONA 500MG"
    assert campos.itens[0]["quantidade"] == 1.0
    assert campos.itens[0]["valor_total_item"] == 1250
    assert campos.itens[1]["valor_total_item"] == 600


def test_extrair_campos_texto_ilegivel_retorna_tudo_none():
    campos = extrair_campos(TEXTO_OCR_ILEGIVEL)
    assert campos.chave_acesso is None
    assert campos.cnpj_emitente is None
    assert campos.data_emissao is None
    assert campos.valor_total is None
    assert campos.itens == []


def test_extrair_campos_nao_levanta_excecao_com_texto_vazio():
    campos = extrair_campos("")
    assert campos.chave_acesso is None
    assert campos.itens == []
