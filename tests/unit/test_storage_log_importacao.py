from __future__ import annotations

from src.models.log_importacao import LogImportacao
from src.storage import db as storage_db


def _preparar_db(tmp_path) -> str:
    db_path = str(tmp_path / "financiall.db")
    storage_db.init_db(db_path)
    return db_path


def test_inserir_e_listar_log_importacao(tmp_path):
    db_path = _preparar_db(tmp_path)

    log = LogImportacao(
        fonte="extrato-teste.xls",
        periodo_inicio="2026-08-01",
        periodo_fim="2026-08-31",
        importadas=3,
        ja_existentes=1,
        puladas=0,
        classificadas_automaticamente=2,
        pendentes_natureza=1,
        reconciliadas=0,
        ambiguas=0,
    )
    log_id = storage_db.inserir_log_importacao(log, db_path=db_path)
    assert log_id is not None

    logs = storage_db.listar_logs_importacao(db_path=db_path)
    assert len(logs) == 1
    assert logs[0].fonte == "extrato-teste.xls"
    assert logs[0].periodo_inicio == "2026-08-01"
    assert logs[0].periodo_fim == "2026-08-31"
    assert logs[0].importadas == 3


def test_listar_log_importacao_ordena_do_mais_recente_para_o_mais_antigo(tmp_path):
    db_path = _preparar_db(tmp_path)

    primeiro = LogImportacao(
        data_hora="2026-09-01T10:00:00",
        fonte="primeiro.xls",
        importadas=1,
        ja_existentes=0,
        puladas=0,
        classificadas_automaticamente=0,
        pendentes_natureza=1,
        reconciliadas=0,
        ambiguas=0,
    )
    segundo = LogImportacao(
        data_hora="2026-09-02T10:00:00",
        fonte="segundo.xls",
        importadas=1,
        ja_existentes=0,
        puladas=0,
        classificadas_automaticamente=0,
        pendentes_natureza=1,
        reconciliadas=0,
        ambiguas=0,
    )
    storage_db.inserir_log_importacao(primeiro, db_path=db_path)
    storage_db.inserir_log_importacao(segundo, db_path=db_path)

    logs = storage_db.listar_logs_importacao(db_path=db_path)
    assert [log.fonte for log in logs] == ["segundo.xls", "primeiro.xls"]


def test_log_importacao_com_fonte_e_periodo_nulos(tmp_path):
    db_path = _preparar_db(tmp_path)

    log = LogImportacao(
        fonte=None,
        periodo_inicio=None,
        periodo_fim=None,
        importadas=0,
        ja_existentes=0,
        puladas=0,
        classificadas_automaticamente=0,
        pendentes_natureza=0,
        reconciliadas=0,
        ambiguas=0,
    )
    storage_db.inserir_log_importacao(log, db_path=db_path)

    logs = storage_db.listar_logs_importacao(db_path=db_path)
    assert logs[0].fonte is None
    assert logs[0].periodo_inicio is None
    assert logs[0].periodo_fim is None
