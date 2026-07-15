from __future__ import annotations


def formatar_data_br(data_iso: str | None) -> str | None:
    """Converte AAAA-MM-DD para DD/MM/AAAA. Retorna a entrada inalterada
    se não bater com o formato esperado (degrada sem quebrar em vez de
    lançar erro numa camada de apresentação)."""
    if not data_iso:
        return data_iso
    partes = data_iso.split("-")
    if len(partes) != 3:
        return data_iso
    ano, mes, dia = partes
    return f"{dia}/{mes}/{ano}"


def formatar_mes_ano_br(mes_iso: str | None) -> str | None:
    """Converte AAAA-MM (usado no resumo mensal) para MM/AAAA."""
    if not mes_iso:
        return mes_iso
    partes = mes_iso.split("-")
    if len(partes) != 2:
        return mes_iso
    ano, mes = partes
    return f"{mes}/{ano}"


def formatar_aamm_br(aamm: str | None) -> str | None:
    """Converte AAMM (2 dígitos de ano + 2 de mês, extraído da chave de
    acesso -- fallback quando a data de emissão completa não está
    disponível) para MM/20AA."""
    if not aamm or len(aamm) != 4 or not aamm.isdigit():
        return aamm
    ano_2_digitos, mes = aamm[:2], aamm[2:]
    return f"{mes}/20{ano_2_digitos}"
