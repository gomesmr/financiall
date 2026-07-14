from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Categoria:
    nome: str
    id: int | None = None
