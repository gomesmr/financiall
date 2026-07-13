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


TEXTO_OCR_FORMATO_X_IGUAL = (
    "MERCADO REAL LTDA\n"
    "CNPJ: 17.608.063/0005-51\n"
    "BANANA NANICA KG 1,400 KG X 6,99 = 9,79\n"
    "TEMP AROMA ERVAS 1 UN X 7,59 = 7,59\n"
    "Valor a Pagar R$ 17,38\n"
)


def test_extrair_campos_reconhece_formato_qtd_x_valor_igual_total():
    """Formato confirmado contra OCR de cupom real (código/descrição
    quantidade UN X valor_unitário = valor_total)."""
    campos = extrair_campos(TEXTO_OCR_FORMATO_X_IGUAL)
    assert campos.cnpj_emitente == "17608063000551"
    assert campos.valor_total == 1738
    assert len(campos.itens) == 2
    assert campos.itens[0]["descricao"] == "BANANA NANICA KG"
    assert campos.itens[0]["quantidade"] == 1.4
    assert campos.itens[0]["valor_unitario"] == 699
    assert campos.itens[0]["valor_total_item"] == 979


def test_extrair_campos_encontra_chave_impressa_em_grupos_de_4_digitos():
    """A chave de acesso impressa no cupom (ao contrário do parâmetro de
    uma URL) costuma vir em grupos de 4 dígitos separados por espaço —
    confirmado contra OCR de cupom real, onde a extração por sequência
    contígua falhava."""
    grupos = [CHAVE[i : i + 4] for i in range(0, len(CHAVE), 4)]
    texto = "Consulte pela Chave de Acesso em\n" + " ".join(grupos) + "\n"
    campos = extrair_campos(texto)
    assert campos.chave_acesso == CHAVE


def test_extrair_campos_chave_grupos_incompletos_nao_encontra_nada():
    """Se o OCR não capturou dígitos suficientes (menos de 44 ao todo na
    linha), não deve inventar uma chave — fica None e a nota cai em
    pendente de revisão, o comportamento esperado (Princípio VII)."""
    texto = "Chave de acesso\n3526 0717 6080\n"
    campos = extrair_campos(texto)
    assert campos.chave_acesso is None
