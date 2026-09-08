from __future__ import annotations

import pytest

from src.services.normalizacao import normalizar_chave_estabelecimento


@pytest.mark.parametrize(
    "descricao_normalizada,esperado",
    [
        ("CLARICELL 09/21", "CLARICELL"),
        ("CLARICELL 12/21", "CLARICELL"),
        ("CLARICELL PARCELA 9 DE 21", "CLARICELL"),
        ("NATURA PAY PARCELA 1 DE 10", "NATURA PAY"),
        ("DROGASIL1327 01/03", "DROGASIL1327"),
        ("MERCADOLIVRE*2PRODUTOS PARCELA 18 DE 18", "MERCADOLIVRE*2PRODUTOS"),
        ("SJX COMERCIAL ATACAD", "SJX COMERCIAL ATACAD"),  # sem sufixo, inalterado
        ("", ""),
        (None, None),
    ],
)
def test_normalizar_chave_estabelecimento(descricao_normalizada, esperado):
    assert normalizar_chave_estabelecimento(descricao_normalizada) == esperado


def test_normalizar_chave_estabelecimento_nao_remove_numero_no_meio():
    """So remove sufixo NN/NN no FINAL da string -- um numero de loja
    embutido no nome (ex.: "DROGASIL1327") nunca deve ser tocado."""
    assert normalizar_chave_estabelecimento("DROGASIL1327") == "DROGASIL1327"
