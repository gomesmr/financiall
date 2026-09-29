from __future__ import annotations

from src.models.transacao import TipoTransacao
from src.services import estabelecimento as estabelecimento_service
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


def reconciliar_gastos_sem_nota(transacao_ids: list[int], db_path: str = storage_db.DEFAULT_DB_PATH) -> int:
    """Reconciliacao disparada depois de uma classificacao manual: a
    importacao so tenta reconciliar o que ja entra como gasto (ou saida
    pendente), entao um gasto classificado a mao depois nunca era cruzado
    com as notas fiscais. Ignora o que nao e gasto de saida ou ja tem nota.
    Retorna quantas foram reconciliadas."""
    reconciliadas = 0
    for transacao_id in transacao_ids:
        transacao = storage_db.buscar_transacao_por_id(transacao_id, db_path=db_path)
        if (
            transacao is None
            or transacao.natureza != "gasto"
            or transacao.tipo != TipoTransacao.SAIDA
            or transacao.nota_fiscal_id is not None
        ):
            continue
        if tentar_reconciliar(transacao_id, transacao.conta, db_path=db_path) == "reconciliada":
            reconciliadas += 1
            estabelecimento_service.resolver_estabelecimento(transacao_id, db_path=db_path)
    return reconciliadas
