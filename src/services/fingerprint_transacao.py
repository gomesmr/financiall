from __future__ import annotations

import hashlib

from src.services.normalizacao import normalizar_descricao


def calcular_fingerprint(data_iso: str, descricao: str, valor_centavos: int, conta_canonica: str) -> str:
    """Mesma formula do script legado importar_extrato.py (research.md #1):
    sha1(data | descricao_normalizada | valor_absoluto_em_centavos | conta)[:16].
    Usada tanto pela migracao historica quanto pelo parser recorrente, para
    que a mesma transacao processada por qualquer um dos dois caminhos
    nunca seja gravada duas vezes (FR-023)."""
    descricao_normalizada = normalizar_descricao(descricao)
    valor_abs = abs(int(valor_centavos))
    base = f"{data_iso}|{descricao_normalizada}|{valor_abs}|{conta_canonica}"
    return hashlib.sha1(base.encode()).hexdigest()[:16]
