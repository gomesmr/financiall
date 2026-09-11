from __future__ import annotations

import pytest

from src.services.importar_historico_extrato import processar_transacoes
from src.storage import db as storage_db


def _preparar_db(tmp_path) -> str:
    db_path = str(tmp_path / "financiall.db")
    storage_db.init_db(db_path)
    return db_path


def _registro(data: str, descricao: str, valor_raw: float, conta: str = "Itaú_CC", fonte: str = "extrato-teste.xls"):
    return {
        "data": data,
        "descricao": descricao,
        "valor_raw": valor_raw,
        "conta": conta,
        "fonte": fonte,
        "titular": "marcelo",
    }


def test_processar_transacoes_grava_log_com_fonte_periodo_e_contagens(tmp_path):
    db_path = _preparar_db(tmp_path)
    registros = [
        _registro("2026-08-05", "COMPRA A", -100.0),
        _registro("2026-08-20", "COMPRA B", -50.0),
        _registro("2026-08-10", "COMPRA C", -30.0),
    ]

    resumo = processar_transacoes(registros, db_path=db_path)

    logs = storage_db.listar_logs_importacao(db_path=db_path)
    assert len(logs) == 1
    log = logs[0]
    assert log.fonte == "extrato-teste.xls"
    assert log.periodo_inicio == "2026-08-05"
    assert log.periodo_fim == "2026-08-20"
    assert log.importadas == resumo.importadas == 3
    assert log.ja_existentes == resumo.ja_existentes == 0
    assert log.puladas == resumo.puladas
    assert log.classificadas_automaticamente == resumo.classificadas_automaticamente
    assert log.pendentes_natureza == resumo.pendentes_natureza
    assert log.reconciliadas == resumo.reconciliadas
    assert log.ambiguas == resumo.ambiguas


def test_processar_transacoes_lista_vazia_gera_log_sem_fonte_nem_periodo(tmp_path):
    db_path = _preparar_db(tmp_path)

    processar_transacoes([], db_path=db_path)

    logs = storage_db.listar_logs_importacao(db_path=db_path)
    assert len(logs) == 1
    assert logs[0].fonte is None
    assert logs[0].periodo_inicio is None
    assert logs[0].periodo_fim is None
    assert logs[0].importadas == 0


def test_reimportar_arquivo_ja_existente_gera_novo_log_com_zero_importadas(tmp_path):
    db_path = _preparar_db(tmp_path)
    registros = [_registro("2026-08-05", "COMPRA A", -100.0), _registro("2026-08-20", "COMPRA B", -50.0)]

    processar_transacoes(registros, db_path=db_path)
    processar_transacoes(registros, db_path=db_path)

    logs = storage_db.listar_logs_importacao(db_path=db_path)
    assert len(logs) == 2
    ultimo, primeiro = logs
    assert primeiro.importadas == 2
    assert primeiro.ja_existentes == 0
    assert ultimo.importadas == 0
    assert ultimo.ja_existentes == 2


def test_registros_sem_data_valida_geram_log_sem_periodo(tmp_path):
    db_path = _preparar_db(tmp_path)
    registros = [_registro("", "COMPRA SEM DATA", -10.0)]

    processar_transacoes(registros, db_path=db_path)

    logs = storage_db.listar_logs_importacao(db_path=db_path)
    assert logs[0].periodo_inicio is None
    assert logs[0].periodo_fim is None
    # o registro sem data e pulado (dado invalido), mas o evento de log
    # ainda e gravado (FR-005)
    assert logs[0].puladas == 1


def test_excecao_no_meio_do_processamento_nao_grava_log(tmp_path, monkeypatch):
    db_path = _preparar_db(tmp_path)
    registros = [_registro("2026-08-05", "COMPRA A", -100.0)]

    def _quebrar(*args, **kwargs):
        raise RuntimeError("falha simulada")

    monkeypatch.setattr(storage_db, "inserir_transacao", _quebrar)

    with pytest.raises(RuntimeError):
        processar_transacoes(registros, db_path=db_path)

    assert storage_db.listar_logs_importacao(db_path=db_path) == []
