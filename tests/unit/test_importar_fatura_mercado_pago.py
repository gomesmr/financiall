from __future__ import annotations

import pytest

from src.services.importar_fatura_mercado_pago import FaturaInvalidaError, parsear_texto

_TEXTO_FATURA_SINTETICA = """\
Marcelo Renato Gomes
Emitida em: 30/06/2026
Olá, Marcelo
Detalhes de consumo
Movimentações na fatura
Data Movimentações Valor em R$
14/06 Pagamento da fatura de junho/2026 R$ 1.822,04
30/06 Juros de mora R$ 3,65
30/06 Multa por atraso R$ 35,98
Cartão Visa [************3258]
Data Movimentações Valor em R$
15/06 MERCADOLIVRE*MERCADOLIVRE Parcela 1 de 4 R$ 13,30
16/06 DL*99 RIDE R$ 9,70
16/06 DL*99 RIDE ESTORNO -R$ 9,70
Total R$ 23,00
Cartão Visa [************4848]
Data Movimentações Valor em R$
11/05 CLARICELL Parcela 14 de 21 R$ 166,66
Total R$ 166,66
"""


def test_reconhece_secao_de_encargos_e_secoes_por_cartao():
    registros = parsear_texto(_TEXTO_FATURA_SINTETICA, fonte="teste.pdf")
    contas = {r["descricao"]: r["conta"] for r in registros}

    assert contas["Juros de mora"] == "MercadoPago"
    assert contas["Multa por atraso"] == "MercadoPago"
    assert contas["MERCADOLIVRE*MERCADOLIVRE Parcela 1 de 4"] == "MercadoPago_3258"
    assert contas["CLARICELL Parcela 14 de 21"] == "MercadoPago_4848"


def test_ignora_cabecalho_de_tabela_e_linha_total():
    registros = parsear_texto(_TEXTO_FATURA_SINTETICA, fonte="teste.pdf")
    descricoes = [r["descricao"] for r in registros]
    assert not any(d.startswith("Total") for d in descricoes)
    assert not any(d.startswith("Data Movimentações") for d in descricoes)


def test_filtra_pagamento_da_fatura_anterior():
    registros = parsear_texto(_TEXTO_FATURA_SINTETICA, fonte="teste.pdf")
    descricoes = [r["descricao"] for r in registros]
    assert not any("pagamento da fatura" in d.lower() for d in descricoes)


def test_preserva_sufixo_parcela_na_descricao():
    registros = parsear_texto(_TEXTO_FATURA_SINTETICA, fonte="teste.pdf")
    descricoes = [r["descricao"] for r in registros]
    assert "MERCADOLIVRE*MERCADOLIVRE Parcela 1 de 4" in descricoes
    assert "CLARICELL Parcela 14 de 21" in descricoes


def test_reconhece_valor_negativo_como_estorno():
    registros = parsear_texto(_TEXTO_FATURA_SINTETICA, fonte="teste.pdf")
    estorno = next(r for r in registros if "ESTORNO" in r["descricao"])
    assert estorno["valor_raw"] == -9.70


def test_infere_ano_igual_ao_de_emissao_quando_mes_e_menor_ou_igual():
    registros = parsear_texto(_TEXTO_FATURA_SINTETICA, fonte="teste.pdf")
    juros = next(r for r in registros if r["descricao"] == "Juros de mora")
    assert juros["data"] == "2026-06-30"


def test_infere_ano_anterior_quando_mes_do_lancamento_e_maior_que_o_de_emissao():
    texto = """\
Emitida em: 15/01/2027
Movimentações na fatura
Data Movimentações Valor em R$
20/12 Juros de mora R$ 5,00
"""
    registros = parsear_texto(texto, fonte="teste.pdf")
    assert registros[0]["data"] == "2026-12-20"


def test_ignora_linha_de_lancamento_antes_de_qualquer_secao_reconhecida():
    texto = """\
Emitida em: 30/06/2026
15/06 Lançamento fora de secao R$ 100,00
Movimentações na fatura
Data Movimentações Valor em R$
30/06 Juros de mora R$ 3,65
"""
    registros = parsear_texto(texto, fonte="teste.pdf")
    assert len(registros) == 1
    assert registros[0]["descricao"] == "Juros de mora"


def test_arquivo_sem_emitida_em_levanta_erro():
    with pytest.raises(FaturaInvalidaError):
        parsear_texto("Texto qualquer sem a data de emissão.", fonte="teste.pdf")


def test_titular_sempre_marcelo():
    registros = parsear_texto(_TEXTO_FATURA_SINTETICA, fonte="teste.pdf")
    assert all(r["titular"] == "marcelo" for r in registros)


def test_fonte_e_repassada_para_cada_registro():
    registros = parsear_texto(_TEXTO_FATURA_SINTETICA, fonte="mercado-pago-2026-06.pdf")
    assert all(r["fonte"] == "mercado-pago-2026-06.pdf" for r in registros)


def test_lancamentos_identicos_no_mesmo_dia_recebem_sufixo_de_ocorrencia():
    """Achado real (fatura de junho/2026): duas corridas de app distintas
    no mesmo dia podem ter a mesma data/descricao/valor arredondado. Sem
    desambiguacao, a segunda teria fingerprint identico a primeira e seria
    descartada como duplicata, perdendo um gasto real."""
    texto = """\
Emitida em: 30/06/2026
Cartão Visa [************3258]
Data Movimentações Valor em R$
17/06 DL*99 RIDE R$ 9,70
17/06 DL*99 RIDE R$ 9,70
18/06 DL*99 RIDE R$ 9,70
"""
    registros = parsear_texto(texto, fonte="teste.pdf")
    descricoes = [r["descricao"] for r in registros]
    assert descricoes == ["DL*99 RIDE", "DL*99 RIDE #2", "DL*99 RIDE"]
