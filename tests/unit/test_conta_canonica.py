from src.services.conta_canonica import canonicalizar_conta, eh_conta_debito


def test_canonicaliza_conta_bb_cristine():
    assert canonicalizar_conta("BB_Cristine") == "bb_cristine_cc"


def test_conta_bb_cristine_e_conta_de_debito():
    assert eh_conta_debito("bb_cristine_cc") is True


def test_canonicaliza_conta_mercado_pago_generica():
    assert canonicalizar_conta("MercadoPago") == "mercado_pago"


def test_canonicaliza_conta_mercado_pago_por_cartao():
    assert canonicalizar_conta("MercadoPago_3258") == "mercado_pago_3258"
    assert canonicalizar_conta("MercadoPago_4848") == "mercado_pago_4848"


def test_canonicaliza_conta_desconhecida_passa_direto():
    assert canonicalizar_conta("Nubank_Qualquer") == "Nubank_Qualquer"


def test_canonicaliza_conta_vazia_ou_none():
    assert canonicalizar_conta(None) == ""
    assert canonicalizar_conta("") == ""
