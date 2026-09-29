from __future__ import annotations

import re

from src.services.normalizacao import normalizar_descricao
from src.storage import db as storage_db

# A mesma transacao vinda de duas fontes (upload de extrato x Open Finance,
# flash.txt x CSV da Flash, dois dumps Open Finance) pode chegar com a data
# deslocada em 1 dia e a descricao escrita de outro jeito -- o fingerprint
# exato (data|descricao|valor|conta) nao reconhece. Achado com dado real em
# 2026-09-29 (11 duplicatas apagadas a mao em producao).
JANELA_DIAS_DUPLICATA = 1

_TAMANHO_MINIMO_PREFIXO = 6
_RE_SUFIXO_DD_MM = re.compile(r"(\d{2})/(\d{2})$")
_RE_PARCELA = re.compile(r"(\d{1,2}/\d{1,2}|PARCELA\d+DE\d+)$")


def _compactar(descricao: str, data_iso: str) -> str:
    """Descricao normalizada sem nenhum espaco e sem marcadores que variam
    entre fontes: '(ESTORNO)' e o sufixo DD/MM quando ele e a propria data
    da transacao ('PIX RECEBIDO ANA MAR10/09' em 2026-09-10). Um sufixo
    NN/NN que nao bate com a data e parcela e fica."""
    texto = normalizar_descricao(descricao).replace("(ESTORNO)", "")
    texto = re.sub(r"\s+", "", texto)
    m = _RE_SUFIXO_DD_MM.search(texto)
    if m and data_iso and m.group(1) == data_iso[8:10] and m.group(2) == data_iso[5:7]:
        texto = texto[: m.start()]
    return texto


def descricoes_compativeis(descricao_a: str, data_a: str, descricao_b: str, data_b: str) -> bool:
    """Iguais depois de compactar, ou -- quando nenhuma das duas tem sufixo
    de parcela -- uma e prefixo da outra (extrato truncado x Open Finance
    completo; 'Depósito' x 'Depósito transferido'). Com parcela exige
    igualdade: 'X 02/03' e 'X 03/03' sao parcelas diferentes, e 'X' sozinho
    pode ser outra parcela que perdeu o sufixo."""
    a = _compactar(descricao_a, data_a)
    b = _compactar(descricao_b, data_b)
    if not a or not b:
        return False
    if a == b:
        return True
    if _RE_PARCELA.search(a) or _RE_PARCELA.search(b):
        return False
    menor, maior = sorted((a, b), key=len)
    return len(menor) >= _TAMANHO_MINIMO_PREFIXO and maior.startswith(menor)


def buscar_duplicata_aproximada(
    conta: str,
    valor: int,
    tipo: str,
    data_iso: str,
    descricao: str,
    ignorar_ids: set[int],
    db_path: str = storage_db.DEFAULT_DB_PATH,
) -> int | None:
    """Id da transacao ja gravada que e a mesma desta (mesma conta, valor e
    tipo, data a ate JANELA_DIAS_DUPLICATA, descricao compativel), ou None.
    `ignorar_ids`: transacoes que nao podem ser reaproveitadas -- as gravadas
    nesta mesma importacao (duas compras iguais em dias seguidos no mesmo
    arquivo sao legitimas) e as ja casadas com outro registro desta
    importacao (cada transacao existente so absorve um registro)."""
    for candidata in storage_db.buscar_candidatas_duplicata(
        conta, valor, tipo, data_iso, JANELA_DIAS_DUPLICATA, db_path=db_path
    ):
        if candidata["id"] in ignorar_ids:
            continue
        if descricoes_compativeis(descricao, data_iso, candidata["descricao"], candidata["data"]):
            return candidata["id"]
    return None
