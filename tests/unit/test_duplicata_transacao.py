from __future__ import annotations

import pytest

from src.services.duplicata_transacao import descricoes_compativeis
from src.services.importar_historico_extrato import processar_transacoes
from src.storage import db as storage_db


@pytest.fixture()
def db_path(tmp_path):
    caminho = str(tmp_path / "financiall.db")
    storage_db.init_db(caminho)
    return caminho


def _registro(data: str, descricao: str, valor_raw: float, fonte: str, conta: str = "Itaú_CC"):
    return {"data": data, "descricao": descricao, "valor_raw": valor_raw, "conta": conta, "fonte": fonte}


def _total_transacoes(db_path) -> int:
    conn = storage_db.get_connection(db_path)
    try:
        return conn.execute("SELECT COUNT(*) FROM transacao").fetchone()[0]
    finally:
        conn.close()


# --- compatibilidade de descricao -----------------------------------------


@pytest.mark.parametrize(
    ("a", "data_a", "b", "data_b"),
    [
        # espacamento diferente entre fontes (Open Finance x dump anterior)
        ("DL*99 RideSAO PAULOBR", "2026-07-29", "DL          *99 RideSAO PAULOBR", "2026-07-29"),
        # extrato truncado com sufixo da propria data x descricao completa
        ("PIX RECEBIDO FULANO DE10/09", "2026-09-10", "Pix recebido FULANO DE TAL SILVA", "2026-09-11"),
        # flash.txt x CSV da Flash
        ("Depósito", "2026-01-29", "Depósito transferido", "2026-01-29"),
        # marcador de estorno so numa das fontes
        ("LOJA QUALQUER (estorno)", "2026-07-21", "LOJA QUALQUER", "2026-07-21"),
        ("Pagamento de boleto EMPRESA X S A", "2026-09-10", "Pagamento de boleto EMPRESA X S A", "2026-09-11"),
    ],
)
def test_descricoes_compativeis_reconhece_mesma_transacao(a, data_a, b, data_b):
    assert descricoes_compativeis(a, data_a, b, data_b)


@pytest.mark.parametrize(
    ("a", "b"),
    [
        # parcelas diferentes da mesma compra
        ("LOJA REFRIGERACA02/03", "LOJA REFRIGERACA03/03"),
        ("LOJA X Parcela 2 de 6", "LOJA X Parcela 6 de 6"),
        # parcela x mesma loja sem sufixo (outra parcela que perdeu o sufixo)
        ("CURSO ONLINE 02/12", "CURSO ONLINE"),
        # estabelecimentos diferentes
        ("PG *99 RIDE", "DL*99 RIDE"),
        # prefixo curto demais pra ser evidencia
        ("PIX", "PIX ENVIADO FULANO"),
    ],
)
def test_descricoes_compativeis_rejeita_transacoes_diferentes(a, b):
    assert not descricoes_compativeis(a, "2026-07-14", b, "2026-07-14")


# --- dedup aproximado na importacao ----------------------------------------


def test_mesma_transacao_de_outra_fonte_com_data_mais_um_dia_nao_duplica(db_path):
    processar_transacoes([_registro("2026-09-10", "Entrada PAGTO Férias", 1000.00, "extrato-upload.json")], db_path=db_path)

    resumo = processar_transacoes(
        [_registro("2026-09-11", "Entrada PAGTO Férias", 1000.00, "openfinance.json")], db_path=db_path
    )

    assert resumo.importadas == 0
    assert resumo.ja_existentes == 1
    assert _total_transacoes(db_path) == 1


def test_data_a_mais_de_um_dia_nao_e_considerada_duplicata(db_path):
    processar_transacoes([_registro("2026-09-10", "Entrada PAGTO Férias", 1000.00, "a.json")], db_path=db_path)

    resumo = processar_transacoes([_registro("2026-09-12", "Entrada PAGTO Férias", 1000.00, "b.json")], db_path=db_path)

    assert resumo.importadas == 1
    assert _total_transacoes(db_path) == 2


def test_compras_iguais_em_dias_seguidos_no_mesmo_arquivo_sao_mantidas(db_path):
    resumo = processar_transacoes(
        [
            _registro("2026-09-10", "Compra débito PADARIA", -12.00, "extrato.json"),
            _registro("2026-09-11", "Compra débito PADARIA", -12.00, "extrato.json"),
        ],
        db_path=db_path,
    )

    assert resumo.importadas == 2
    assert _total_transacoes(db_path) == 2


def test_cada_transacao_existente_absorve_so_um_registro(db_path):
    processar_transacoes([_registro("2026-09-10", "Compra débito PADARIA", -12.00, "a.json")], db_path=db_path)

    # a outra fonte traz a mesma compra do dia 10 (espacamento diferente) e
    # uma compra nova igual no dia 11 -- so a do dia 10 e duplicata
    resumo = processar_transacoes(
        [
            _registro("2026-09-11", "Compra débito  PADARIA", -12.00, "b.json"),
            _registro("2026-09-10", "Compra débito  PADARIA", -12.00, "b.json"),
        ],
        db_path=db_path,
    )

    assert resumo.ja_existentes == 1
    assert resumo.importadas == 1
    assert _total_transacoes(db_path) == 2


def test_fingerprint_exato_tem_prioridade_sobre_casamento_aproximado(db_path):
    processar_transacoes([_registro("2026-09-10", "Compra débito PADARIA", -12.00, "a.json")], db_path=db_path)

    # o registro do dia 11 vem antes no arquivo; sem reservar o casamento
    # exato do dia 10 primeiro, ele "roubaria" a transacao existente
    resumo = processar_transacoes(
        [
            _registro("2026-09-11", "Compra débito PADARIA", -12.00, "b.json"),
            _registro("2026-09-10", "Compra débito PADARIA", -12.00, "b.json"),
        ],
        db_path=db_path,
    )

    assert resumo.ja_existentes == 1
    assert resumo.importadas == 1
    assert _total_transacoes(db_path) == 2


def test_parcelas_diferentes_na_mesma_data_nao_sao_duplicatas(db_path):
    processar_transacoes(
        [_registro("2026-07-14", "LOJA REFRIGERACA02/03", 300.00, "a.json", conta="Itaú_1035")], db_path=db_path
    )

    resumo = processar_transacoes(
        [_registro("2026-07-14", "LOJA REFRIGERACA03/03", 300.00, "b.json", conta="Itaú_1035")], db_path=db_path
    )

    assert resumo.importadas == 1
    assert _total_transacoes(db_path) == 2
