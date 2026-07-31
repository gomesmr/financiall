from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class TipoTransacao(str, Enum):
    ENTRADA = "entrada"
    SAIDA = "saida"


class NaturezaTransacao(str, Enum):
    GASTO = "gasto"
    RENDA = "renda"
    TRANSFERENCIA_INTERNA = "transferencia_interna"
    PAGAMENTO_FATURA = "pagamento_fatura"
    ESTORNO_CREDITO = "estorno_credito"


NATUREZAS_VALIDAS = {n.value for n in NaturezaTransacao}


@dataclass
class Transacao:
    fingerprint: str
    data: str
    descricao: str
    valor: int
    tipo: TipoTransacao
    conta: str
    id: int | None = None
    descricao_normalizada: str | None = None
    natureza: str | None = None
    metodo_classificacao_natureza: str | None = None
    categoria_id: int | None = None
    titular: str | None = None
    fonte: str | None = None
    nota_fiscal_id: int | None = None
    estabelecimento_id: int | None = None
    data_importacao: str = ""

    def __post_init__(self) -> None:
        if not self.data_importacao:
            self.data_importacao = datetime.now().isoformat()
