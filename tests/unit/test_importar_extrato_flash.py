from __future__ import annotations

import pytest

from src.services.importar_extrato_flash import parsear


def _criar_extrato_flash(caminho, linhas: list[str]):
    cabecalho = "Data,Hora,Movimentação,Valor,Meio de Pagamento,Saldo"
    caminho.write_text("\n".join([cabecalho] + linhas), encoding="utf-8-sig")
    return str(caminho)


@pytest.fixture
def arquivo_extrato(tmp_path):
    def _criar(linhas):
        caminho = tmp_path / "flash_extrato_05-2026_abc.csv"
        return _criar_extrato_flash(caminho, linhas)

    return _criar


def test_converte_valor_negativo_com_nbsp_entre_rs_e_numero(arquivo_extrato):
    """Achado no dado real: o espaco entre 'R$' e o numero e um NBSP
    (\xa0), nao um espaco comum -- pra valor negativo, o NBSP fica
    sanduichado entre o sinal e o digito ('-R$\xa072,00'), o que quebra
    float() se so o espaco comum for removido (float so ignora espaco em
    branco no inicio/fim da string)."""
    caminho = arquivo_extrato(["30/05/2026,21:17,LA GALLEGA E LENHA GRI,\"-R$\xa072,00\",Cartão,\"R$\xa01.241,32\""])
    registros = parsear(caminho)
    assert len(registros) == 1
    assert registros[0]["valor_raw"] == -72.0


def test_converte_valor_positivo(arquivo_extrato):
    caminho = arquivo_extrato(["28/05/2026,03:44,Depósito transferido,\"R$\xa01.440,00\",Depósito,\"R$\xa01.519,31\""])
    registros = parsear(caminho)
    assert registros[0]["valor_raw"] == 1440.0


def test_preserva_data_iso_e_descricao(arquivo_extrato):
    caminho = arquivo_extrato(["13/05/2026,07:37,VILLA GRANO Sao Paulo BRA,\"-R$\xa03,38\",Cartão,\"R$\xa079,31\""])
    registros = parsear(caminho)
    assert registros[0]["data"] == "2026-05-13"
    assert registros[0]["descricao"] == "VILLA GRANO Sao Paulo BRA"


def test_conta_e_titular_fixos(arquivo_extrato):
    caminho = arquivo_extrato(["13/05/2026,07:37,VILLA GRANO Sao Paulo BRA,\"-R$\xa03,38\",Cartão,\"R$\xa079,31\""])
    registros = parsear(caminho)
    assert registros[0]["conta"] == "Flash"
    assert registros[0]["titular"] == "marcelo"


def test_arquivo_vazio_retorna_lista_vazia(arquivo_extrato):
    caminho = arquivo_extrato([])
    assert parsear(caminho) == []
