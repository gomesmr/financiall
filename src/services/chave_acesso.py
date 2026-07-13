from __future__ import annotations

import itertools
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

TAMANHO_CHAVE = 44

# Tabela de codigo IBGE de UF usada nas posicoes 1-2 da chave de acesso.
_UF_POR_CODIGO = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP",
    "17": "TO", "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB",
    "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES",
    "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS",
    "51": "MT", "52": "GO", "53": "DF",
}

_DIGITOS_RE = re.compile(r"\d+")


class ChaveInvalidaError(ValueError):
    """Entrada nao contem uma chave de acesso valida de 44 digitos."""


@dataclass(frozen=True)
class DadosChave:
    chave_acesso: str
    uf: str | None
    cnpj_emitente: str
    ano_mes_emissao: str
    modelo: str


def calcular_digito_verificador(chave_43_digitos: str) -> int:
    """Algoritmo modulo 11 padrao do modelo nacional de NF-e/NFC-e
    (research.md #4): pesos ciclicos 2-9 da direita para a esquerda sobre
    os 43 primeiros digitos."""
    pesos = itertools.cycle([2, 3, 4, 5, 6, 7, 8, 9])
    soma = sum(int(digito) * peso for digito, peso in zip(reversed(chave_43_digitos), pesos))
    resto = soma % 11
    return 0 if resto in (0, 1) else 11 - resto


def _passa_no_digito_verificador(candidato_44_digitos: str) -> bool:
    if len(candidato_44_digitos) != TAMANHO_CHAVE or not candidato_44_digitos.isdigit():
        return False
    dv_informado = int(candidato_44_digitos[-1])
    dv_calculado = calcular_digito_verificador(candidato_44_digitos[:-1])
    return dv_informado == dv_calculado


def _candidatos_em_texto(texto: str) -> list[str]:
    """Extrai, de um texto qualquer, candidatas de 44 digitos: runs exatos
    de 44 digitos, e janelas deslizantes de 44 digitos dentro de runs
    maiores (research.md #3)."""
    candidatos: list[str] = []
    for run in _DIGITOS_RE.findall(texto):
        if len(run) == TAMANHO_CHAVE:
            candidatos.append(run)
        elif len(run) > TAMANHO_CHAVE:
            for inicio in range(0, len(run) - TAMANHO_CHAVE + 1):
                candidatos.append(run[inicio : inicio + TAMANHO_CHAVE])
    return candidatos


def encontrar_chave_valida_em_texto(texto: str) -> str | None:
    """Procura, em qualquer texto (usado tanto para um valor de query
    string quanto para o texto bruto reconhecido por OCR — research.md
    #9), uma sequência de 44 dígitos que passe no dígito verificador.
    Retorna a primeira encontrada, ou None."""
    for candidato in _candidatos_em_texto(texto):
        if _passa_no_digito_verificador(candidato):
            return candidato
    return None


def extrair_chave_de_url(url: str) -> str | None:
    """Procura, em cada valor de parametro de consulta da URL, uma
    sequencia de 44 digitos valida pelo digito verificador (FR-002,
    research.md #3). Retorna None se nao encontrar nenhuma."""
    try:
        query = urlparse(url).query
    except ValueError:
        return None
    if not query:
        return None
    valores = parse_qs(query)
    for lista_valores in valores.values():
        for valor in lista_valores:
            if chave := encontrar_chave_valida_em_texto(valor):
                return chave
    return None


def normalizar_chave_colada(entrada: str) -> str:
    """Remove espacos e qualquer caractere nao numerico (FR-003)."""
    return re.sub(r"\D", "", entrada)


def extrair_e_validar(entrada: str) -> str:
    """Ponto de entrada usado pelo importador: aceita uma URL ou uma chave
    colada (com ou sem caracteres nao numericos) e retorna a chave de 44
    digitos validada. Levanta ChaveInvalidaError com mensagem em portugues
    quando nao for possivel (FR-004)."""
    entrada = entrada.strip()

    if entrada.lower().startswith(("http://", "https://")):
        chave = extrair_chave_de_url(entrada)
        if chave is None:
            raise ChaveInvalidaError(
                f'Não foi possível identificar uma chave de acesso válida de 44 dígitos em "{entrada}".'
            )
        return chave

    normalizada = normalizar_chave_colada(entrada)
    if len(normalizada) != TAMANHO_CHAVE:
        raise ChaveInvalidaError(
            f'Não foi possível identificar uma chave de acesso válida de 44 dígitos em "{entrada}".'
        )
    if not _passa_no_digito_verificador(normalizada):
        raise ChaveInvalidaError(
            "A chave de acesso informada tem dígito verificador inválido."
        )
    return normalizada


def decodificar_chave(chave_acesso: str) -> DadosChave:
    """Decodifica UF, ano-mes de emissao, CNPJ do emitente e modelo
    diretamente dos 44 digitos (research.md #5), sem depender de rede."""
    if len(chave_acesso) != TAMANHO_CHAVE or not chave_acesso.isdigit():
        raise ChaveInvalidaError("Chave de acesso deve ter 44 dígitos numéricos para ser decodificada.")
    codigo_uf = chave_acesso[0:2]
    return DadosChave(
        chave_acesso=chave_acesso,
        uf=_UF_POR_CODIGO.get(codigo_uf),
        ano_mes_emissao=chave_acesso[2:6],
        cnpj_emitente=chave_acesso[6:20],
        modelo=chave_acesso[20:22],
    )
