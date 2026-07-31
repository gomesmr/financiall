from __future__ import annotations

import pytest

from src.models.nota_fiscal import CanalOrigem, NotaFiscal, StatusNota
from src.models.transacao import Transacao, TipoTransacao
from src.services import reconciliacao
from src.storage import db as storage_db
from tests.helpers import gerar_chave_valida


@pytest.fixture()
def db_path(tmp_path):
    caminho = str(tmp_path / "financiall.db")
    storage_db.init_db(caminho)
    return caminho


_contador_notas = 0


def _inserir_nota(valor_total: int, data_emissao: str, db_path) -> int:
    global _contador_notas
    _contador_notas += 1
    nota = NotaFiscal(
        canal_origem=CanalOrigem.URL_CHAVE,
        status=StatusNota.COMPLETA,
        chave_acesso=gerar_chave_valida(numero=str(_contador_notas).zfill(9)),
        valor_total=valor_total,
        data_emissao=data_emissao,
    )
    return storage_db.inserir_nota(nota, db_path=db_path)


def _inserir_transacao(valor: int, data: str, conta: str, db_path, fingerprint: str | None = None) -> int:
    transacao = Transacao(
        fingerprint=fingerprint or f"fp-{valor}-{data}-{conta}",
        data=data,
        descricao="COMPRA QUALQUER",
        valor=valor,
        tipo=TipoTransacao.SAIDA,
        conta=conta,
        natureza="gasto",
    )
    return storage_db.inserir_transacao(transacao, db_path=db_path)


# --- match unico -------------------------------------------------------


def test_reconciliar_transacao_match_unico_liga_automaticamente(db_path):
    nota_id = _inserir_nota(15000, "2026-06-10", db_path=db_path)
    transacao_id = _inserir_transacao(15000, "2026-07-05", "itau_2486", db_path=db_path)

    resultado = reconciliacao.tentar_reconciliar(transacao_id, "itau_2486", db_path=db_path)

    assert resultado == "reconciliada"
    transacao = storage_db.buscar_transacao_por_id(transacao_id, db_path=db_path)
    assert transacao.nota_fiscal_id == nota_id


def test_reconciliar_transacao_sem_candidato_segue_sem_vinculo(db_path):
    transacao_id = _inserir_transacao(9999, "2026-07-05", "itau_2486", db_path=db_path)

    resultado = reconciliacao.tentar_reconciliar(transacao_id, "itau_2486", db_path=db_path)

    assert resultado == "sem_candidato"
    transacao = storage_db.buscar_transacao_por_id(transacao_id, db_path=db_path)
    assert transacao.nota_fiscal_id is None


def test_reconciliar_transacao_multiplos_candidatos_fica_ambigua(db_path):
    _inserir_nota(5000, "2026-06-20", db_path=db_path)
    _inserir_nota(5000, "2026-06-21", db_path=db_path)
    transacao_id = _inserir_transacao(5000, "2026-07-01", "itau_2486", db_path=db_path)

    resultado = reconciliacao.tentar_reconciliar(transacao_id, "itau_2486", db_path=db_path)

    assert resultado == "ambigua"
    transacao = storage_db.buscar_transacao_por_id(transacao_id, db_path=db_path)
    assert transacao.nota_fiscal_id is None


def test_reconciliar_transacao_nota_fora_da_janela_nao_e_candidata(db_path):
    _inserir_nota(3000, "2026-01-01", db_path=db_path)  # bem antes da janela de cartao (45 dias)
    transacao_id = _inserir_transacao(3000, "2026-07-05", "itau_2486", db_path=db_path)

    resultado = reconciliacao.tentar_reconciliar(transacao_id, "itau_2486", db_path=db_path)

    assert resultado == "sem_candidato"


def test_reconciliar_transacao_janela_debito_mais_curta_que_cartao(db_path):
    """research.md #3: conta corrente (debito) usa janela de 3 dias; uma
    nota emitida 10 dias antes nao deve casar para conta de debito, mesmo
    que casasse para cartao (45 dias)."""
    _inserir_nota(2000, "2026-06-25", db_path=db_path)
    transacao_id = _inserir_transacao(2000, "2026-07-05", "itau_cc", db_path=db_path)

    resultado = reconciliacao.tentar_reconciliar(transacao_id, "itau_cc", db_path=db_path)

    assert resultado == "sem_candidato"


def test_reconciliar_transacao_nota_ja_reconciliada_nao_e_candidata_de_novo(db_path):
    nota_id = _inserir_nota(7000, "2026-06-10", db_path=db_path)
    transacao_1 = _inserir_transacao(7000, "2026-07-01", "itau_2486", db_path=db_path, fingerprint="fp-1")
    reconciliacao.tentar_reconciliar(transacao_1, "itau_2486", db_path=db_path)

    transacao_2 = _inserir_transacao(7000, "2026-07-02", "itau_2486", db_path=db_path, fingerprint="fp-2")
    resultado = reconciliacao.tentar_reconciliar(transacao_2, "itau_2486", db_path=db_path)

    assert resultado == "sem_candidato"
    transacao_2_atual = storage_db.buscar_transacao_por_id(transacao_2, db_path=db_path)
    assert transacao_2_atual.nota_fiscal_id is None


# --- desvincular / vincular manual --------------------------------------


def test_desvincular_reconciliacao_transacao_sem_nota_retorna_none(db_path):
    transacao_id = _inserir_transacao(100, "2026-07-01", "itau_2486", db_path=db_path)
    resultado = storage_db.desvincular_reconciliacao(transacao_id, db_path=db_path)
    assert resultado is None


def test_desvincular_reconciliacao_remove_vinculo(db_path):
    nota_id = _inserir_nota(15000, "2026-06-10", db_path=db_path)
    transacao_id = _inserir_transacao(15000, "2026-07-05", "itau_2486", db_path=db_path)
    reconciliacao.tentar_reconciliar(transacao_id, "itau_2486", db_path=db_path)

    resultado = storage_db.desvincular_reconciliacao(transacao_id, db_path=db_path)

    assert resultado is True
    transacao = storage_db.buscar_transacao_por_id(transacao_id, db_path=db_path)
    assert transacao.nota_fiscal_id is None


def test_vincular_reconciliacao_manual_nota_ja_vinculada_retorna_false(db_path):
    nota_id = _inserir_nota(15000, "2026-06-10", db_path=db_path)
    transacao_1 = _inserir_transacao(15000, "2026-07-05", "itau_2486", db_path=db_path, fingerprint="fp-a")
    reconciliacao.tentar_reconciliar(transacao_1, "itau_2486", db_path=db_path)

    transacao_2 = _inserir_transacao(999, "2026-07-06", "itau_2486", db_path=db_path, fingerprint="fp-b")
    resultado = storage_db.vincular_reconciliacao_manual(transacao_2, nota_id, db_path=db_path)

    assert resultado is False


def test_listar_reconciliacoes_pendentes_inclui_caso_ambiguo(db_path):
    _inserir_nota(5000, "2026-06-20", db_path=db_path)
    _inserir_nota(5000, "2026-06-21", db_path=db_path)
    transacao_id = _inserir_transacao(5000, "2026-07-01", "itau_2486", db_path=db_path)
    reconciliacao.tentar_reconciliar(transacao_id, "itau_2486", db_path=db_path)

    casos = storage_db.listar_reconciliacoes_pendentes(db_path=db_path)

    assert len(casos) == 2  # uma entrada por nota candidata, ambas com a mesma transacao
    for caso in casos:
        assert caso["candidatos"][0]["transacao_id"] == transacao_id
