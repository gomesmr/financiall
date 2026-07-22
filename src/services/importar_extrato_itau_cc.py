from __future__ import annotations

import os
from datetime import datetime

import xlrd

# Toda conta corrente importada por este parser e a do Marcelo (mesma
# unica conta corrente Itau usada desde a feature 010) -- fixo, sem
# heuristica (mesmo espirito de research.md #7 da feature 011).
CONTA = "Itaú_CC"
TITULAR = "marcelo"


def _data_iso(valor_bruto) -> str | None:
    texto = str(valor_bruto).strip()
    if not texto:
        return None
    try:
        return datetime.strptime(texto, "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def parsear(caminho_arquivo: str) -> list[dict]:
    """Le um extrato de conta corrente do Itau (.xls) e retorna uma lista
    de registros no mesmo formato aceito por
    importar_historico_extrato.processar_transacoes -- parser recorrente
    que faltava (so existia a migracao historica pontual via
    registro.json ate a feature 011 US3; achado ao processar um extrato
    novo real do usuario, que baixou direto do banco sem passar pelo
    script legado). Colunas: data | lancamento | ag./origem | valor (R$) |
    saldos (R$). Linhas de saldo ('SALDO ANTERIOR', 'SALDO TOTAL
    DISPONIVEL DIA') nunca tem valor numerico na coluna de valor -- caem
    fora sozinhas pelo mesmo filtro que já descarta cabecalho/metadados,
    sem precisar de lista de exclusao por texto."""
    workbook = xlrd.open_workbook(caminho_arquivo)
    planilha = workbook.sheet_by_index(0)
    fonte = os.path.basename(caminho_arquivo)

    registros: list[dict] = []
    for linha in range(planilha.nrows):
        celulas = [planilha.cell_value(linha, coluna) for coluna in range(planilha.ncols)]
        if len(celulas) < 4:
            continue
        data_bruta, descricao_bruta, _origem, valor_bruto = celulas[0], celulas[1], celulas[2], celulas[3]

        if not isinstance(valor_bruto, (int, float)):
            continue
        descricao = str(descricao_bruta).strip() if descricao_bruta else ""
        if not descricao:
            continue
        data_iso = _data_iso(data_bruta)
        if not data_iso:
            continue

        registros.append(
            {
                "data": data_iso,
                "descricao": descricao,
                "valor_raw": float(valor_bruto),
                "conta": CONTA,
                "fonte": fonte,
                "titular": TITULAR,
            }
        )

    return registros
