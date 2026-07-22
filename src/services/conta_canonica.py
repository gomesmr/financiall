from __future__ import annotations

import re

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
    "Itaú_1035": "itau_1035",
    "Itaú_CC": "itau_cc",
    "Flash": "flash",
    "BB_Cristine": "bb_cristine_cc",
}

# Cobre cartoes futuros no formato "Itaú_<4 digitos>" (research.md #10) sem
# precisar de uma entrada nova em CONTA_CANONICA por numero de cartao.
_RE_CARTAO_GENERICO = re.compile(r"^Itaú_(\d{4})$")


def canonicalizar_conta(conta: str | None) -> str:
    """Retorna a identidade canonica da conta. Conta desconhecida (nao
    mapeada) passa direto, sem falhar -- degrada sem quebrar o fluxo
    (research.md #2, mesmo espirito do Principio VII)."""
    if not conta:
        return ""
    if conta in CONTA_CANONICA:
        return CONTA_CANONICA[conta]
    match = _RE_CARTAO_GENERICO.match(conta)
    if match:
        return f"itau_{match.group(1)}"
    return conta


def eh_conta_debito(conta_canonica: str) -> bool:
    """Contas de debito/conta corrente usam janela de reconciliacao mais
    curta que cartao de credito (research.md #3)."""
    return conta_canonica.endswith("_cc")
