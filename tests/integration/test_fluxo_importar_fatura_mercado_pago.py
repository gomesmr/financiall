from __future__ import annotations

from src.services.importar_fatura_mercado_pago import parsear_texto
from src.services.importar_historico_extrato import processar_transacoes
from src.storage import db as storage_db

_TEXTO_FATURA_SINTETICA = """\
Marcelo Renato Gomes
Emitida em: 30/06/2026
Movimentações na fatura
Data Movimentações Valor em R$
14/06 Pagamento da fatura de junho/2026 R$ 1.822,04
30/06 Juros de mora R$ 3,65
30/06 Multa por atraso R$ 35,98
Cartão Visa [************3258]
Data Movimentações Valor em R$
15/06 MERCADOLIVRE*MERCADOLIVRE Parcela 1 de 4 R$ 13,30
16/06 DL*99 RIDE R$ 9,70
Total R$ 23,00
Cartão Visa [************4848]
Data Movimentações Valor em R$
11/05 CLARICELL Parcela 14 de 21 R$ 166,66
Total R$ 166,66
"""


def test_parser_e_persistencia_compartilhada_classificam_e_nao_duplicam(tmp_path):
    db_path = str(tmp_path / "financiall.db")
    storage_db.init_db(db_path)

    registros = parsear_texto(_TEXTO_FATURA_SINTETICA, fonte="mercado-pago-2026-06.pdf")

    primeira = processar_transacoes(registros, db_path=db_path)
    segunda = processar_transacoes(registros, db_path=db_path)

    # 4 lancamentos reais: Juros de mora, Multa por atraso, MERCADOLIVRE,
    # DL*99 RIDE, CLARICELL -- "Pagamento da fatura" ja foi filtrado pelo
    # parser, entao nao entra na contagem.
    assert primeira.importadas == 5
    assert segunda.importadas == 0
    assert segunda.ja_existentes == 5


def test_parcela_seguinte_da_mesma_compra_nao_e_tratada_como_duplicata(tmp_path):
    """Valida research.md #4 (achado critico): a parcela 15 de uma compra
    parcelada, com a mesma data original e valor da parcela 14 ja
    importada, deve entrar como transacao nova -- nao pode ser descartada
    como "ja existente" so porque data/valor/conta coincidem."""
    db_path = str(tmp_path / "financiall.db")
    storage_db.init_db(db_path)

    texto_fatura_junho = """\
Emitida em: 30/06/2026
Cartão Visa [************4848]
Data Movimentações Valor em R$
11/05 CLARICELL Parcela 14 de 21 R$ 166,66
Total R$ 166,66
"""
    texto_fatura_julho = """\
Emitida em: 30/07/2026
Cartão Visa [************4848]
Data Movimentações Valor em R$
11/05 CLARICELL Parcela 15 de 21 R$ 166,66
Total R$ 166,66
"""

    registros_junho = parsear_texto(texto_fatura_junho, fonte="mercado-pago-2026-06.pdf")
    registros_julho = parsear_texto(texto_fatura_julho, fonte="mercado-pago-2026-07.pdf")

    resumo_junho = processar_transacoes(registros_junho, db_path=db_path)
    resumo_julho = processar_transacoes(registros_julho, db_path=db_path)

    assert resumo_junho.importadas == 1
    assert resumo_julho.importadas == 1
    assert resumo_julho.ja_existentes == 0

    transacoes = storage_db.listar_transacoes(conta="mercado_pago_4848", db_path=db_path)
    assert len(transacoes) == 2
