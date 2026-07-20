from __future__ import annotations

from src.services.conta_canonica import eh_conta_debito
from src.storage import db as storage_db

JANELA_DIAS_DEBITO = 3
JANELA_DIAS_CARTAO = 45


def tentar_reconciliar(transacao_id: int, conta_canonica: str, db_path: str = storage_db.DEFAULT_DB_PATH) -> str:
    """Orquestra a reconciliacao de uma transacao (research.md #3/#7):
    calcula a janela de data conforme o tipo de conta e delega o match a
    storage_db.reconciliar_transacao. Retorna 'reconciliada' | 'ambigua' |
    'sem_candidato'."""
    janela = JANELA_DIAS_DEBITO if eh_conta_debito(conta_canonica) else JANELA_DIAS_CARTAO
    return storage_db.reconciliar_transacao(transacao_id, janela, db_path=db_path)
