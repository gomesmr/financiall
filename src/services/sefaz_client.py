from __future__ import annotations

import re
from dataclasses import dataclass, field

import requests

TIMEOUT_SEGUNDOS = 5

_TAG_RE = re.compile(r"<[^>]+>")
_ESPACOS_RE = re.compile(r"\s+")
_VALOR_TOTAL_RE = re.compile(
    r"valor\s+total[^0-9]{0,20}(\d{1,3}(?:\.\d{3})*,\d{2})", re.IGNORECASE
)
_DATA_RE = re.compile(r"(\d{2})/(\d{2})/(\d{4})")
_EMITENTE_RE = re.compile(
    r"(?:raz[aã]o\s+social|nome\s*/\s*raz[aã]o\s+social)[:\s]*([A-ZÀ-Úa-zà-ú0-9][^\n<]{2,80})",
    re.IGNORECASE,
)
_LINHA_TABELA_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
_CELULA_RE = re.compile(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", re.IGNORECASE | re.DOTALL)
_NUMERO_BR_RE = re.compile(r"^\d{1,3}(?:\.\d{3})*,\d{2,4}$")


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


def _extrair_itens_de_tabelas(html: str) -> list[dict]:
    """Heurística genérica (não específica de UF): trata qualquer linha de
    tabela HTML cujas duas últimas células pareçam números em formato
    brasileiro (qtd e valor) como um item — funciona para portais que
    listam itens em `<table>`, mesmo sem conhecer o layout exato de cada
    estado; linhas que não casam esse padrão (cabeçalhos, totais) são
    ignoradas silenciosamente."""
    itens: list[dict] = []
    for linha_html in _LINHA_TABELA_RE.findall(html):
        celulas = [_texto_sem_tags(c) for c in _CELULA_RE.findall(linha_html)]
        if len(celulas) < 3:
            continue
        *descricao_partes, quantidade_txt, valor_txt = celulas
        if not (_NUMERO_BR_RE.match(quantidade_txt) and _NUMERO_BR_RE.match(valor_txt)):
            continue
        descricao = " ".join(p for p in descricao_partes if p).strip()
        if not descricao:
            continue
        try:
            quantidade = float(quantidade_txt.replace(".", "").replace(",", "."))
            valor_total_item = _valor_para_centavos(valor_txt)
        except ValueError:
            continue
        itens.append(
            {
                "codigo_item": None,
                "descricao": descricao,
                "quantidade": quantidade,
                "valor_unitario": None,
                "valor_total_item": valor_total_item,
            }
        )
    return itens


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

    emitente_nome = None
    if match_emitente := _EMITENTE_RE.search(texto):
        emitente_nome = match_emitente.group(1).strip()

    return DadosNotaSefaz(
        emitente_nome=emitente_nome,
        data_emissao=data_emissao,
        valor_total=valor_total,
        itens=_extrair_itens_de_tabelas(html),
    )
