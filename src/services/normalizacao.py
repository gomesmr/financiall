from __future__ import annotations

import re
import unicodedata

# Dicionário de expansão de abreviações -- curado a partir do corpus real
# (tests/fixtures/corpus_descricoes_produtos.txt), não uma lista genérica
# especulativa (research.md #1). "H" isolado (ex.: "PAPEL H CARINHO") não
# entra apesar de aparecer 17 vezes no corpus -- token de uma letra só é
# risco alto demais de falso positivo em descrições futuras não relacionadas
# a papel higiênico (Princípio I: expandir só o que é seguro, não só o que
# é frequente).
ABREVIACOES: dict[str, str] = {
    "HIGIE": "HIGIENICO",
}


def normalizar_descricao(descricao: str | None) -> str:
    """Maiúsculas, sem acentuação (unicodedata, stdlib -- research.md #1),
    espaços colapsados, abreviações conhecidas expandidas. `None`/vazia
    retorna string vazia -- o chamador (classificar_item, research.md #20)
    é quem decide o que fazer com isso, não esta função."""
    if not descricao:
        return ""

    texto = descricao.strip().upper()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"\s+", " ", texto).strip()

    if not texto:
        return ""

    palavras = [ABREVIACOES.get(palavra, palavra) for palavra in texto.split(" ")]
    return " ".join(palavras)
