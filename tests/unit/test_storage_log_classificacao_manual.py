from __future__ import annotations

from src.models.log_classificacao_manual import LogClassificacaoManual
from src.storage import db as storage_db


def _preparar_db(tmp_path) -> str:
    db_path = str(tmp_path / "financiall.db")
    storage_db.init_db(db_path)
    return db_path


def test_inserir_e_listar_log_classificacao_grupo(tmp_path):
    db_path = _preparar_db(tmp_path)
    categoria_id = storage_db.criar_categoria("Restaurante/lazer", db_path=db_path)

    log = LogClassificacaoManual(
        metodo="grupo",
        alvo_descricao_normalizada="BURGER KING",
        natureza="gasto",
        categoria_id=categoria_id,
        quantidade_afetada=3,
    )
    log_id = storage_db.inserir_log_classificacao_manual(log, db_path=db_path)
    assert log_id is not None

    logs = storage_db.listar_logs_classificacao_manual(db_path=db_path)
    assert len(logs) == 1
    assert logs[0].metodo == "grupo"
    assert logs[0].alvo_descricao_normalizada == "BURGER KING"
    assert logs[0].alvo_transacao_id is None
    assert logs[0].categoria_id == categoria_id
    assert logs[0].quantidade_afetada == 3


def test_inserir_e_listar_log_classificacao_individual(tmp_path):
    db_path = _preparar_db(tmp_path)

    log = LogClassificacaoManual(
        metodo="individual",
        alvo_transacao_id=42,
        natureza="renda",
        categoria_id=None,
        quantidade_afetada=1,
    )
    storage_db.inserir_log_classificacao_manual(log, db_path=db_path)

    logs = storage_db.listar_logs_classificacao_manual(db_path=db_path)
    assert logs[0].metodo == "individual"
    assert logs[0].alvo_transacao_id == 42
    assert logs[0].alvo_descricao_normalizada is None
    assert logs[0].categoria_id is None


def test_listar_log_classificacao_ordena_do_mais_recente_para_o_mais_antigo(tmp_path):
    db_path = _preparar_db(tmp_path)

    primeiro = LogClassificacaoManual(
        data_hora="2026-09-01T10:00:00",
        metodo="grupo",
        alvo_descricao_normalizada="A",
        natureza="renda",
        quantidade_afetada=1,
    )
    segundo = LogClassificacaoManual(
        data_hora="2026-09-02T10:00:00",
        metodo="grupo",
        alvo_descricao_normalizada="B",
        natureza="renda",
        quantidade_afetada=1,
    )
    storage_db.inserir_log_classificacao_manual(primeiro, db_path=db_path)
    storage_db.inserir_log_classificacao_manual(segundo, db_path=db_path)

    logs = storage_db.listar_logs_classificacao_manual(db_path=db_path)
    assert [log.alvo_descricao_normalizada for log in logs] == ["B", "A"]
