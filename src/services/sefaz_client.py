from __future__ import annotations

import re
from dataclasses import dataclass, field

import requests

TIMEOUT_SEGUNDOS = 5

_TAG_RE = re.compile(r"<[^>]+>")
_ESPACOS_RE = re.compile(r"\s+")
_VALOR_TOTAL_RE = re.compile(
    r"(?:valor\s+total|total\s+r\$|total\s+a\s+pagar|valor\s+a\s+pagar)[^0-9]{0,40}(\d{1,3}(?:\.\d{3})*,\d{2})",
    re.IGNORECASE,
)
_DATA_RE = re.compile(r"(\d{2})/(\d{2})/(\d{4})")
_EMITENTE_LABEL_RE = re.compile(
    r"(?:raz[aã]o\s+social|nome\s*/\s*raz[aã]o\s+social)[:\s]*([A-ZÀ-Úa-zà-ú0-9][^\n<]{2,80})",
    re.IGNORECASE,
)
# "DOCUMENTO AUXILIAR DA NOTA FISCAL DE CONSUMIDOR ELETRÔNICA" e o titulo
# padrao nacional obrigatorio em toda NFC-e (nao especifico de UF); o nome
# do emitente costuma vir logo em seguida, antes do rotulo "CNPJ".
_EMITENTE_HEADER_NACIONAL_RE = re.compile(
    r"documento\s+auxiliar\s+da\s+nota\s+fiscal\s+de\s+consumidor\s+eletr[oô]nica\s*(.+?)\s*CNPJ",
    re.IGNORECASE,
)
_LINHA_TABELA_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
_CELULA_RE = re.compile(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", re.IGNORECASE | re.DOTALL)
_NUMERO_BR_RE = re.compile(r"^\d{1,3}(?:\.\d{3})*,\d{2,4}$")

# Spans usados por um layout nacional de referencia (XSLT) adotado por
# varios portais de UF para o detalhamento de item (confirmado contra
# portal real de SP) — tentado primeiro; portais com outro layout caem no
# fallback generico de celulas de tabela.
_ITEM_DESCRICAO_RE = re.compile(r'class="txtTit"[^>]*>\s*([^<]+?)\s*<', re.IGNORECASE)
_ITEM_CODIGO_RE = re.compile(r"C[oó]digo:\s*([^\s<)]+)", re.IGNORECASE)
_ITEM_QTD_RE = re.compile(r"Qtde\.?\s*:?\s*</strong>\s*([\d.,]+)", re.IGNORECASE)
_ITEM_VALOR_UNIT_RE = re.compile(r"Vl\.?\s*Unit\.?\s*:?\s*</strong>\s*([\d.,]+)", re.IGNORECASE)
_ITEM_VALOR_TOTAL_RE = re.compile(r'class="valor"[^>]*>\s*([\d.,]+)\s*<', re.IGNORECASE)


@dataclass(frozen=True)
class DadosNotaSefaz:
    emitente_nome: str | None = None
    data_emissao: str | None = None  # formato AAAA-MM-DD
    valor_total: int | None = None  # centavos
    itens: list[dict] = field(default_factory=list)


class BuscaSefazIndisponivelError(Exception):
    """Falha ao buscar os dados completos na fonte SEFAZ (timeout, erro
    HTTP, ou corpo de resposta inesperado) — sempre capturada
    explicitamente pelo chamador (Princípio III), nunca propagada como
    exceção não tratada."""


def buscar_dados_nota(url: str) -> DadosNotaSefaz:
    """Uma única tentativa HTTP com timeout curto contra a própria URL do
    QR Code (research.md #2/#6) — evita manter uma tabela de portais por
    UF: a URL do QR Code já é a página de consulta correta do portal que
    emitiu a nota."""
    try:
        resposta = requests.get(url, timeout=TIMEOUT_SEGUNDOS)
        resposta.raise_for_status()
    except requests.RequestException as exc:
        raise BuscaSefazIndisponivelError(str(exc)) from exc

    try:
        return _parsear_html(resposta.text)
    except Exception as exc:
        raise BuscaSefazIndisponivelError(f"Resposta inesperada da fonte SEFAZ: {exc}") from exc


def _texto_sem_tags(html: str) -> str:
    sem_tags = _TAG_RE.sub(" ", html)
    return _ESPACOS_RE.sub(" ", sem_tags).strip()


def _valor_para_centavos(valor_br: str) -> int:
    sem_milhar = valor_br.replace(".", "")
    reais, centavos = sem_milhar.split(",")
    return int(reais) * 100 + int(centavos)


def _item_por_spans_nacionais(linha_html: str) -> dict | None:
    """Extrai um item a partir dos spans do layout de referência nacional
    (`txtTit`/`RCod`/`Rqtd`/`RvlUnit`/`valor`) — mais preciso que o
    fallback genérico de células quando o portal usa esse layout."""
    match_descricao = _ITEM_DESCRICAO_RE.search(linha_html)
    match_valor_total = _ITEM_VALOR_TOTAL_RE.search(linha_html)
    if not match_descricao or not match_valor_total:
        return None

    descricao = match_descricao.group(1).strip()
    if len(descricao) < 3:
        return None
    try:
        valor_total_item = _valor_para_centavos(match_valor_total.group(1))
    except ValueError:
        return None

    codigo_item = None
    if match_codigo := _ITEM_CODIGO_RE.search(linha_html):
        codigo_item = match_codigo.group(1).strip()

    quantidade = None
    if match_qtd := _ITEM_QTD_RE.search(linha_html):
        try:
            quantidade = float(match_qtd.group(1).replace(".", "").replace(",", "."))
        except ValueError:
            quantidade = None

    valor_unitario = None
    if match_valor_unit := _ITEM_VALOR_UNIT_RE.search(linha_html):
        try:
            valor_unitario = _valor_para_centavos(match_valor_unit.group(1))
        except ValueError:
            valor_unitario = None

    return {
        "codigo_item": codigo_item,
        "descricao": descricao,
        "quantidade": quantidade,
        "valor_unitario": valor_unitario,
        "valor_total_item": valor_total_item,
    }


def _item_por_celulas_genericas(linha_html: str) -> dict | None:
    """Heurística genérica (não específica de UF): trata uma linha de
    tabela HTML com 3+ células, cujas duas últimas pareçam números em
    formato brasileiro (qtd e valor), como um item — fallback para
    portais que não usam o layout de referência nacional."""
    celulas = [_texto_sem_tags(c) for c in _CELULA_RE.findall(linha_html)]
    if len(celulas) < 3:
        return None
    *descricao_partes, quantidade_txt, valor_txt = celulas
    if not (_NUMERO_BR_RE.match(quantidade_txt) and _NUMERO_BR_RE.match(valor_txt)):
        return None
    descricao = " ".join(p for p in descricao_partes if p).strip()
    if not descricao:
        return None
    try:
        quantidade = float(quantidade_txt.replace(".", "").replace(",", "."))
        valor_total_item = _valor_para_centavos(valor_txt)
    except ValueError:
        return None
    return {
        "codigo_item": None,
        "descricao": descricao,
        "quantidade": quantidade,
        "valor_unitario": None,
        "valor_total_item": valor_total_item,
    }


def _extrair_itens_de_tabelas(html: str) -> list[dict]:
    itens: list[dict] = []
    for linha_html in _LINHA_TABELA_RE.findall(html):
        item = _item_por_spans_nacionais(linha_html) or _item_por_celulas_genericas(linha_html)
        if item is not None:
            itens.append(item)
    return itens


def _extrair_emitente_nome(texto: str) -> str | None:
    if match := _EMITENTE_HEADER_NACIONAL_RE.search(texto):
        nome = match.group(1).strip(" :-")
        if len(nome) >= 3:
            return nome
    if match := _EMITENTE_LABEL_RE.search(texto):
        return match.group(1).strip()
    return None


def _parsear_html(html: str) -> DadosNotaSefaz:
    """Heurísticas leves sobre o texto da página (research.md #9, mesma
    filosofia usada para o texto de OCR) — o layout varia por portal
    estadual, então cada campo é opcional e a ausência de um deles não
    interrompe a extração dos demais (Princípio VII)."""
    texto = _texto_sem_tags(html)

    valor_total = None
    if match_valor := _VALOR_TOTAL_RE.search(texto):
        valor_total = _valor_para_centavos(match_valor.group(1))

    data_emissao = None
    if match_data := _DATA_RE.search(texto):
        dia, mes, ano = match_data.groups()
        data_emissao = f"{ano}-{mes}-{dia}"

    return DadosNotaSefaz(
        emitente_nome=_extrair_emitente_nome(texto),
        data_emissao=data_emissao,
        valor_total=valor_total,
        itens=_extrair_itens_de_tabelas(html),
    )
