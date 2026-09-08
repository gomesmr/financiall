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


# Sufixo de parcela no final da descricao ja normalizada -- "PARCELA X DE Y"
# por extenso (Mercado Pago) ou so "NN/NN" numerico (Itau: "CLARICELL
# 09/21", "DROGASIL1327 01/03"). Usado so pra resolver IDENTIDADE de
# estabelecimento, nunca pro fingerprint da transacao (que precisa manter
# o sufixo pra nao colidir entre parcelas diferentes da mesma compra).
_RE_PARCELA_PALAVRA = re.compile(r"\s+PARCELA\s+\d+\s+DE\s+\d+$")
_RE_PARCELA_NUMERICA = re.compile(r"\s+\d{1,2}/\d{1,2}$")


def normalizar_chave_estabelecimento(descricao_normalizada: str) -> str:
    """Remove o sufixo de parcela do final de uma descricao ja normalizada,
    pra usar como chave de identidade do estabelecimento. Sem isso, cada
    parcela de uma compra financiada (ex.: "CLARICELL PARCELA 9 DE 21",
    "NATURA PAY PARCELA 1 DE 10", "DROGASIL1327 01/03") cria um
    estabelecimento pendente separado -- achado real processando compras
    parceladas, exigia merge manual parcela a parcela toda vez."""
    if not descricao_normalizada:
        return descricao_normalizada
    chave = _RE_PARCELA_PALAVRA.sub("", descricao_normalizada)
    chave = _RE_PARCELA_NUMERICA.sub("", chave)
    return chave.strip() or descricao_normalizada
