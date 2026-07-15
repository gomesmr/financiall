from __future__ import annotations

from src.api.filters import formatar_aamm_br, formatar_data_br, formatar_mes_ano_br


def test_formatar_data_br_converte_iso_para_br():
    assert formatar_data_br("2026-07-15") == "15/07/2026"


def test_formatar_data_br_none_permanece_none():
    assert formatar_data_br(None) is None


def test_formatar_data_br_valor_inesperado_retorna_inalterado():
    assert formatar_data_br("não disponível") == "não disponível"


def test_formatar_mes_ano_br_converte_iso_para_br():
    assert formatar_mes_ano_br("2026-07") == "07/2026"


def test_formatar_mes_ano_br_none_permanece_none():
    assert formatar_mes_ano_br(None) is None


def test_formatar_aamm_br_converte_para_mes_ano_completo():
    assert formatar_aamm_br("2607") == "07/2026"


def test_formatar_aamm_br_valor_invalido_retorna_inalterado():
    assert formatar_aamm_br("abc") == "abc"
    assert formatar_aamm_br("123") == "123"
    assert formatar_aamm_br(None) is None
