from __future__ import annotations

import re
import unicodedata

# Dicionário de expansão de abreviações -- curado a partir do corpus real
# (tests/fixtures/corpus_descricoes_produtos.txt), não uma lista genérica
# especulativa (research.md #1). Populado na Tarefa T030 (US3); vazio até lá
# não quebra a cascata -- só significa que menos descrições abreviadas batem
# no cache/regra antes da curadoria acontecer.
ABREVIACOES: dict[str, str] = {}


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
