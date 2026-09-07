from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class CompromissoFuturo:
    """Parcelamento/dívida cadastrada manualmente para projetar quanto vai
    vencer nos próximos meses -- diferente de Transacao, que só registra o
    que já aconteceu. `parcela_atual`/`mes_referencia` fixam um ponto de
    partida conhecido (ex.: "parcela 1/4 cai em outubro/2026"); o resto é
    projetado a partir daí (ver services/compromissos_futuros.py)."""

    descricao: str
    valor_parcela: int  # centavos
    parcela_atual: int
    total_parcelas: int
    mes_referencia: str  # AAAA-MM em que parcela_atual vence
    id: int | None = None
    conta: str | None = None
    titular: str | None = None
    ativo: bool = True
    data_cadastro: str = ""

    def __post_init__(self) -> None:
        if not self.data_cadastro:
            self.data_cadastro = datetime.now().isoformat()
