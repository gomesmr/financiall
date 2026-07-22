from __future__ import annotations

from src.services.importar_historico_extrato import processar_transacoes
from src.storage import db as storage_db


def _init_db(tmp_path):
    db_path = str(tmp_path / "financiall.db")
    storage_db.init_db(db_path)
    return db_path


def test_encargo_generico_mercado_pago_e_saida(tmp_path):
    db_path = _init_db(tmp_path)
    registros = [
        {
            "data": "2026-06-30",
            "descricao": "Juros do rotativo",
            "valor_raw": 65.23,
            "conta": "MercadoPago",
            "fonte": "mercado-pago-2026-06.pdf",
            "titular": "marcelo",
        }
    ]

    processar_transacoes(registros, db_path=db_path)

    transacoes = storage_db.listar_transacoes(conta="mercado_pago", db_path=db_path)
    assert len(transacoes) == 1
    assert transacoes[0].tipo.value == "saida"


def test_compra_cartao_mercado_pago_e_saida_estorno_e_entrada(tmp_path):
    db_path = _init_db(tmp_path)
    registros = [
        {
            "data": "2026-06-15",
            "descricao": "MERCADOLIVRE*MERCADOLIVRE",
            "valor_raw": 152.99,
            "conta": "MercadoPago_3258",
            "fonte": "mercado-pago-2026-06.pdf",
            "titular": "marcelo",
        },
        {
            "data": "2026-06-16",
            "descricao": "MERCADOLIVRE*MERCADOLIVRE ESTORNO",
            "valor_raw": -50.00,
            "conta": "MercadoPago_3258",
            "fonte": "mercado-pago-2026-06.pdf",
            "titular": "marcelo",
        },
    ]

    processar_transacoes(registros, db_path=db_path)

    transacoes = storage_db.listar_transacoes(conta="mercado_pago_3258", db_path=db_path)
    compra = next(t for t in transacoes if t.valor == 15299)
    estorno = next(t for t in transacoes if t.valor == 5000)
    assert compra.tipo.value == "saida"
    assert estorno.tipo.value == "entrada"
