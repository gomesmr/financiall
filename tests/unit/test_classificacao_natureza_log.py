from __future__ import annotations

from src.models.transacao import Transacao, TipoTransacao
from src.storage import db as storage_db


def _preparar_db(tmp_path) -> str:
    db_path = str(tmp_path / "financiall.db")
    storage_db.init_db(db_path)
    return db_path


def _criar_transacao_pendente(db_path: str, descricao_normalizada: str, fingerprint: str) -> int:
    transacao = Transacao(
        fingerprint=fingerprint,
        data="2026-08-05",
        descricao=descricao_normalizada,
        descricao_normalizada=descricao_normalizada,
        valor=1000,
        tipo=TipoTransacao("saida"),
        conta="itau_cc",
    )
    return storage_db.inserir_transacao(transacao, db_path=db_path)


def test_classificar_grupo_pendente_grava_log_com_quantidade_afetada(tmp_path):
    db_path = _preparar_db(tmp_path)
    categoria_id = storage_db.criar_categoria("Restaurante/lazer", db_path=db_path)
    _criar_transacao_pendente(db_path, "BURGER KING", "fp1")
    _criar_transacao_pendente(db_path, "BURGER KING", "fp2")

    quantidade = storage_db.classificar_grupo_pendente_natureza(
        "BURGER KING", "gasto", categoria_id, db_path=db_path
    )

    assert quantidade == 2
    logs = storage_db.listar_logs_classificacao_manual(db_path=db_path)
    assert len(logs) == 1
    assert logs[0].metodo == "grupo"
    assert logs[0].alvo_descricao_normalizada == "BURGER KING"
    assert logs[0].natureza == "gasto"
    assert logs[0].categoria_id == categoria_id
    assert logs[0].quantidade_afetada == 2


def test_atribuir_natureza_manual_grava_log_individual(tmp_path):
    db_path = _preparar_db(tmp_path)
    transacao_id = _criar_transacao_pendente(db_path, "PIX RECEBIDO ANA", "fp3")

    resultado = storage_db.atribuir_natureza_manual(transacao_id, "renda", None, db_path=db_path)

    assert resultado is True
    logs = storage_db.listar_logs_classificacao_manual(db_path=db_path)
    assert len(logs) == 1
    assert logs[0].metodo == "individual"
    assert logs[0].alvo_transacao_id == transacao_id
    assert logs[0].natureza == "renda"
    assert logs[0].quantidade_afetada == 1


def test_reclassificar_o_mesmo_grupo_gera_dois_eventos(tmp_path):
    db_path = _preparar_db(tmp_path)
    categoria_id = storage_db.criar_categoria("Farmácia", db_path=db_path)
    _criar_transacao_pendente(db_path, "DROGASIL", "fp4")

    storage_db.classificar_grupo_pendente_natureza("DROGASIL", "gasto", categoria_id, db_path=db_path)
    # reclassifica (mesma transacao ja tem natureza, mas a funcao so busca
    # pendentes -- para simular reclassificacao de verdade, criamos outra
    # pendente com a mesma descricao e classificamos como natureza diferente
    _criar_transacao_pendente(db_path, "DROGASIL", "fp5")
    storage_db.classificar_grupo_pendente_natureza("DROGASIL", "estorno_credito", None, db_path=db_path)

    logs = storage_db.listar_logs_classificacao_manual(db_path=db_path)
    assert len(logs) == 2
    assert [log.natureza for log in logs] == ["estorno_credito", "gasto"]


def test_classificar_grupo_sem_transacao_pendente_nao_grava_log(tmp_path):
    db_path = _preparar_db(tmp_path)

    quantidade = storage_db.classificar_grupo_pendente_natureza(
        "DESCRICAO INEXISTENTE", "renda", None, db_path=db_path
    )

    assert quantidade == 0
    assert storage_db.listar_logs_classificacao_manual(db_path=db_path) == []


def test_atribuir_natureza_manual_invalida_nao_grava_log(tmp_path):
    db_path = _preparar_db(tmp_path)
    transacao_id = _criar_transacao_pendente(db_path, "ALGO", "fp6")

    resultado = storage_db.atribuir_natureza_manual(transacao_id, "natureza-invalida", None, db_path=db_path)

    assert resultado is False
    assert storage_db.listar_logs_classificacao_manual(db_path=db_path) == []


def test_atribuir_natureza_manual_transacao_inexistente_nao_grava_log(tmp_path):
    db_path = _preparar_db(tmp_path)

    resultado = storage_db.atribuir_natureza_manual(99999, "renda", None, db_path=db_path)

    assert resultado is None
    assert storage_db.listar_logs_classificacao_manual(db_path=db_path) == []
