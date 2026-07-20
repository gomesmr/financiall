from __future__ import annotations

# Consolida grafias diferentes da mesma conta fisica do sistema legado
# (research.md #2) -- aplicado antes de calcular fingerprint e antes de
# persistir, tanto na migracao historica quanto no parser recorrente, para
# que as duas grafias antigas produzam sempre o mesmo fingerprint.
CONTA_CANONICA: dict[str, str] = {
    "2486": "itau_2486",
    "Itaú_2486": "itau_2486",
    "9073": "itau_9073",
    "Itaú_9073": "itau_9073",
    "1035": "itau_1035",
    "Itaú_CC": "itau_cc",
    "Flash": "flash",
}


def canonicalizar_conta(conta: str | None) -> str:
    """Retorna a identidade canonica da conta. Conta desconhecida (nao
    mapeada) passa direto, sem falhar -- degrada sem quebrar o fluxo
    (research.md #2, mesmo espirito do Principio VII)."""
    if not conta:
        return ""
    return CONTA_CANONICA.get(conta, conta)


def eh_conta_debito(conta_canonica: str) -> bool:
    """Contas de debito/conta corrente usam janela de reconciliacao mais
    curta que cartao de credito (research.md #3)."""
    return conta_canonica.endswith("_cc")
