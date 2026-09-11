from __future__ import annotations

from src.models.transacao import Transacao, TipoTransacao
from src.storage import db as storage_db


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


def test_pagina_log_classificacoes_lista_evento_apos_classificacao_em_grupo(app_e_db, client):
    _, db_path = app_e_db
    categoria_id = storage_db.criar_categoria("Restaurante/lazer", db_path=db_path)
    _criar_transacao_pendente(db_path, "BURGER KING", "fp1")

    resposta = client.post(
        "/transacoes/pendentes/classificar-grupo",
        json={"descricao_normalizada": "BURGER KING", "natureza": "gasto", "categoria_id": categoria_id},
    )
    assert resposta.status_code == 200

    corpo = client.get("/ver/log-classificacoes").get_data(as_text=True)
    assert "BURGER KING" in corpo
    assert "Restaurante/lazer" in corpo


def test_pagina_log_classificacoes_lista_evento_apos_edicao_individual(app_e_db, client):
    _, db_path = app_e_db
    transacao_id = _criar_transacao_pendente(db_path, "PIX RECEBIDO ANA", "fp2")

    resposta = client.put(f"/transacoes/{transacao_id}/natureza", json={"natureza": "renda"})
    assert resposta.status_code == 200

    corpo = client.get("/ver/log-classificacoes").get_data(as_text=True)
    assert f"#{transacao_id}" in corpo
    assert "Individual" in corpo


def test_pagina_log_classificacoes_sem_evento_mostra_estado_vazio(app_e_db, client):
    resposta = client.get("/ver/log-classificacoes")

    assert resposta.status_code == 200
    assert "Nenhuma classificação manual registrada ainda." in resposta.get_data(as_text=True)
