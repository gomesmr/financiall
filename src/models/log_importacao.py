from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class LogImportacao:
    """Um evento de histórico por execução concluída de
    `processar_transacoes()` -- não se relaciona a uma Transacao
    individual, é um registro agregado por execução (data-model.md,
    feature 014). Existe para responder "quando foi a última importação
    desta fonte e o que ela cobriu?" sem precisar consultar o banco de
    produção diretamente."""

    importadas: int
    ja_existentes: int
    puladas: int
    classificadas_automaticamente: int
    pendentes_natureza: int
    reconciliadas: int
    ambiguas: int
    id: int | None = None
    fonte: str | None = None
    periodo_inicio: str | None = None
    periodo_fim: str | None = None
    data_hora: str = ""

    def __post_init__(self) -> None:
        if not self.data_hora:
            self.data_hora = datetime.now().isoformat()
