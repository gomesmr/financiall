from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.services.chave_acesso import encontrar_chave_valida_em_texto

_CNPJ_RE = re.compile(r"\b(\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})\b")
_VALOR_TOTAL_RE = re.compile(
    r"(?:valor\s+total|total\s+r\$|total\s+a\s+pagar)[^0-9]{0,40}(\d{1,3}(?:\.\d{3})*,\d{2})",
    re.IGNORECASE,
)
_DATA_RE = re.compile(r"(\d{2})/(\d{2})/(\d{4})")
_VALOR_TOKEN_RE = re.compile(r"\d{1,3}(?:\.\d{3})*,\d{2}")
_QTD_TOKEN_RE = re.compile(r"\d+(?:,\d{1,3})?")
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


def _extrair_itens_de_linhas(texto_ocr: str) -> list[dict]:
    """Reconhece linhas no formato `descrição ... quantidade valor`,
    comum em cupons fiscais (os dois últimos tokens da linha). Itens são o
    campo mais frágil de extrair via OCR de texto corrido (research.md
    #9): linhas que não casam esse padrão (cabeçalhos, CNPJ, datas, linha
    de total) são silenciosamente ignoradas — resultado tipicamente
    incompleto, o que é esperado e aceito (Princípio VII)."""
    itens: list[dict] = []
    for linha in texto_ocr.splitlines():
        tokens = linha.strip().split()
        if len(tokens) < 3:
            continue
        valor_token, qtd_token = tokens[-1], tokens[-2]
        if not _VALOR_TOKEN_RE.fullmatch(valor_token) or not _QTD_TOKEN_RE.fullmatch(qtd_token):
            continue
        descricao = " ".join(tokens[:-2]).strip(" -:")
        if len(descricao) < 3:
            continue
        try:
            quantidade = float(qtd_token.replace(",", "."))
            valor_total_item = _valor_para_centavos(valor_token)
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
    chave = encontrar_chave_valida_em_texto(texto_ocr)

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
