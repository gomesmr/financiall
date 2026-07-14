from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class StatusNota(str, Enum):
    COMPLETA = "completa"
    PENDENTE_REVISAO = "pendente_revisao"


class CanalOrigem(str, Enum):
    URL_CHAVE = "url_chave"
    FOTO_PDF = "foto_pdf"


@dataclass
class NotaFiscal:
    canal_origem: CanalOrigem
    status: StatusNota
    id: int | None = None
    chave_acesso: str | None = None
    hash_conteudo: str | None = None
    uf: str | None = None
    cnpj_emitente: str | None = None
    ano_mes_emissao: str | None = None
    modelo: str | None = None
    emitente_nome: str | None = None
    data_emissao: str | None = None
    valor_total: int | None = None
    data_importacao: str = field(default_factory=lambda: datetime.now().isoformat())
    categoria_id: int | None = None
    titular: str | None = None

    def __post_init__(self) -> None:
        if not self.chave_acesso and not self.hash_conteudo:
            raise ValueError(
                "NotaFiscal precisa de chave_acesso ou hash_conteudo (regra de identidade)"
            )
