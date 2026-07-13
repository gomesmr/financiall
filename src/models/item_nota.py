from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ItemNota:
    nota_fiscal_id: int
    id: int | None = None
    codigo_item: str | None = None
    descricao: str | None = None
    quantidade: float | None = None
    valor_unitario: int | None = None
    valor_total_item: int | None = None
