from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class LogClassificacaoManual:
    """Um evento de histórico por ação de classificação manual de
    natureza já concluída com sucesso -- não se relaciona a uma
    Transacao individual, é um registro por ação (em grupo ou
    individual), podendo representar várias transações afetadas de uma
    vez (data-model.md, feature 015)."""

    metodo: str  # "grupo" ou "individual"
    natureza: str
    quantidade_afetada: int
    id: int | None = None
    alvo_descricao_normalizada: str | None = None
    alvo_transacao_id: int | None = None
    categoria_id: int | None = None
    data_hora: str = ""

    def __post_init__(self) -> None:
        if not self.data_hora:
            self.data_hora = datetime.now().isoformat()
