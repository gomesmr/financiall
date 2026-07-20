from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Estabelecimento:
    id: int | None = None
    documento: str | None = None
    descricao_normalizada: str | None = None
    nome_fantasia: str | None = None
    tipo_categoria_id: int | None = None
