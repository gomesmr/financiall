from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.services.chave_acesso import TAMANHO_CHAVE, encontrar_chave_valida_em_texto

_CNPJ_RE = re.compile(r"\b(\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})\b")
_VALOR_TOTAL_RE = re.compile(
    r"(?:valor\s+total|total\s+r\$|total\s+a\s+pagar|valor\s+a\s+pagar|total\s+geral)[^0-9]{0,40}(\d{1,3}(?:\.\d{3})*,\d{2})",
    re.IGNORECASE,
)
_DATA_RE = re.compile(r"(\d{2})/(\d{2})/(\d{4})")
_VALOR_TOKEN_RE = re.compile(r"\d{1,3}(?:\.\d{3})*,\d{2}")
_QTD_TOKEN_RE = re.compile(r"\d+(?:,\d{1,3})?")
_LINHA_ITEM_X_IGUAL_RE = re.compile(
    r"(?P<qtd>\d+(?:,\d{1,3})?)\s*[A-Za-zÇç]{1,4}\s*[xX]\s*"
    r"(?P<unit>\d{1,3}(?:\.\d{3})*,\d{2})\s*=\s*(?P<total>\d{1,3}(?:\.\d{3})*,\d{2})"
)
_PALAVRAS_CABECALHO_RE = re.compile(r"[a-zà-ú]+")
_PALAVRAS_CABECALHO_IGNORAR = {
    "cupom", "fiscal", "eletronico", "eletrônico", "nota", "sat", "nfce",
    "consumidor", "extrato", "documento", "auxiliar",
}


@dataclass(frozen=True)
class CamposExtraidos:
    chave_acesso: str | None = None
    emitente_nome: str | None = None
    cnpj_emitente: str | None = None
    data_emissao: str | None = None
    valor_total: int | None = None
    itens: list[dict] = field(default_factory=list)


def _valor_para_centavos(valor_br: str) -> int:
    sem_milhar = valor_br.replace(".", "")
    reais, centavos = sem_milhar.split(",")
    return int(reais) * 100 + int(centavos)


def _normalizar_cnpj(cnpj_formatado: str) -> str:
    return re.sub(r"\D", "", cnpj_formatado)


def _linha_para_item_formato_x_igual(linha: str) -> dict | None:
    """Formato comum em cupons de mercado: `código descrição qtd UN X
    valor_unit = valor_total` (ex.: `BANANA NANICA KG 1,400 KG X 6,99 =
    9,79`) — confirmado contra OCR de cupom real."""
    match = _LINHA_ITEM_X_IGUAL_RE.search(linha)
    if not match:
        return None
    descricao = linha[: match.start()].strip(" -:")
    if len(descricao) < 3:
        return None
    try:
        quantidade = float(match.group("qtd").replace(",", "."))
        valor_unitario = _valor_para_centavos(match.group("unit"))
        valor_total_item = _valor_para_centavos(match.group("total"))
    except ValueError:
        return None
    return {
        "codigo_item": None,
        "descricao": descricao,
        "quantidade": quantidade,
        "valor_unitario": valor_unitario,
        "valor_total_item": valor_total_item,
    }


def _linha_para_item_formato_simples(linha: str) -> dict | None:
    """Formato mais simples: `descrição ... quantidade valor` (os dois
    últimos tokens da linha), sem separador `X`/`=` explícito."""
    tokens = linha.split()
    if len(tokens) < 3:
        return None
    valor_token, qtd_token = tokens[-1], tokens[-2]
    if not _VALOR_TOKEN_RE.fullmatch(valor_token) or not _QTD_TOKEN_RE.fullmatch(qtd_token):
        return None
    descricao = " ".join(tokens[:-2]).strip(" -:")
    if len(descricao) < 3:
        return None
    try:
        quantidade = float(qtd_token.replace(",", "."))
        valor_total_item = _valor_para_centavos(valor_token)
    except ValueError:
        return None
    return {
        "codigo_item": None,
        "descricao": descricao,
        "quantidade": quantidade,
        "valor_unitario": None,
        "valor_total_item": valor_total_item,
    }


def _extrair_itens_de_linhas(texto_ocr: str) -> list[dict]:
    """Tenta reconhecer cada linha como um item, em dois formatos comuns de
    cupom fiscal (research.md #9). Itens são o campo mais frágil de
    extrair via OCR de texto corrido: linhas que não casam nenhum dos dois
    formatos (cabeçalhos, CNPJ, datas, linha de total) são silenciosamente
    ignoradas — resultado tipicamente incompleto, o que é esperado e
    aceito (Princípio VII)."""
    itens: list[dict] = []
    for linha in texto_ocr.splitlines():
        linha = linha.strip()
        if not linha:
            continue
        item = _linha_para_item_formato_x_igual(linha) or _linha_para_item_formato_simples(linha)
        if item is not None:
            itens.append(item)
    return itens


def _encontrar_chave_em_texto_ocr(texto_ocr: str) -> str | None:
    """A chave de acesso impressa no cupom costuma vir em grupos de 4
    dígitos separados por espaço (ex.: `3526 0717 6080 ...`), não como uma
    sequência contínua — diferente do parâmetro de uma URL de QR Code.
    Tenta primeiro a extração padrão (sequência contígua); se não achar,
    concatena os dígitos de cada linha (e de pares de linhas consecutivas,
    para o caso da chave quebrar em duas linhas por causa da largura do
    cupom) e tenta de novo."""
    if chave := encontrar_chave_valida_em_texto(texto_ocr):
        return chave

    linhas = texto_ocr.splitlines()
    for indice, linha in enumerate(linhas):
        so_digitos = re.sub(r"\D", "", linha)
        if len(so_digitos) >= TAMANHO_CHAVE and (chave := encontrar_chave_valida_em_texto(so_digitos)):
            return chave
        if indice + 1 < len(linhas):
            so_digitos_par = re.sub(r"\D", "", linha + linhas[indice + 1])
            if len(so_digitos_par) >= TAMANHO_CHAVE and (
                chave := encontrar_chave_valida_em_texto(so_digitos_par)
            ):
                return chave
    return None


def _adivinhar_emitente_nome(texto_ocr: str) -> str | None:
    """A primeira linha "de conteúdo" do cupom costuma ser o nome do
    emitente; linhas compostas só de palavras de cabeçalho genérico
    ("CUPOM FISCAL...") ou só de dígitos/símbolos são ignoradas. É uma
    heurística fraca por natureza — nunca é o único campo usado para
    calcular o status da nota (Princípio VII)."""
    for linha in texto_ocr.splitlines():
        linha = linha.strip()
        if len(linha) < 3:
            continue
        if re.fullmatch(r"[\d\W]+", linha):
            continue
        palavras = set(_PALAVRAS_CABECALHO_RE.findall(linha.lower()))
        if palavras and palavras.issubset(_PALAVRAS_CABECALHO_IGNORAR):
            continue
        return linha
    return None


def extrair_campos(texto_ocr: str) -> CamposExtraidos:
    """Heurísticas leves sobre o texto reconhecido por OCR de um cupom
    fiscal (research.md #9): cada campo é opcional, texto ruidoso é
    esperado, e a ausência de um deles não impede a extração dos demais
    (Princípio VII)."""
    chave = _encontrar_chave_em_texto_ocr(texto_ocr)

    cnpj = None
    if match_cnpj := _CNPJ_RE.search(texto_ocr):
        cnpj = _normalizar_cnpj(match_cnpj.group(1))

    valor_total = None
    if match_valor := _VALOR_TOTAL_RE.search(texto_ocr):
        valor_total = _valor_para_centavos(match_valor.group(1))

    data_emissao = None
    if match_data := _DATA_RE.search(texto_ocr):
        dia, mes, ano = match_data.groups()
        data_emissao = f"{ano}-{mes}-{dia}"

    return CamposExtraidos(
        chave_acesso=chave,
        emitente_nome=_adivinhar_emitente_nome(texto_ocr),
        cnpj_emitente=cnpj,
        data_emissao=data_emissao,
        valor_total=valor_total,
        itens=_extrair_itens_de_linhas(texto_ocr),
    )
