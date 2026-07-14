from __future__ import annotations

from src.services.chave_acesso import calcular_digito_verificador


def gerar_chave_valida(
    uf: str = "35",
    aamm: str = "2606",
    cnpj: str = "12345678000199",
    modelo: str = "65",
    serie: str = "001",
    numero: str = "000000123",
    tp_emis: str = "1",
    cnf: str = "00000001",
) -> str:
    """Monta uma chave de acesso de 44 dígitos sintaticamente válida (com
    dígito verificador correto) para uso em testes, sem depender de uma
    chave real."""
    base = uf + aamm + cnpj + modelo + serie + numero + tp_emis + cnf
    assert len(base) == 43, f"base com {len(base)} dígitos, esperado 43"
    return base + str(calcular_digito_verificador(base))
