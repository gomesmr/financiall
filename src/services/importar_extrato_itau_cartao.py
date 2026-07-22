from __future__ import annotations

import os
import re

import xlrd

# Linhas de cabecalho/resumo da fatura que nunca sao lancamento de compra
# (mesmo filtro do script legado importar_extrato.py) -- comparadas em
# minusculas.
_DESCRICOES_IGNORADAS = {
    "lançamento",
    "data",
    "logotipo itaú",
    "",
    "lançamentos nacionais",
    "lançamentos internacionais",
    "encargos e serviços",
    "total",
    "subtotal",
    "emitido",
    "melhor",
    "compras feitas",
    "dólar de conversão",
    "valor em dólar",
}


def _conta_pelo_nome_arquivo(caminho_arquivo: str) -> str:
    """Identifica o cartao pelos 4 digitos finais que o Itau usa no nome do
    arquivo exportado (ex.: 9073, 2486, 1035) -- generico o bastante para
    cartoes novos, sem precisar hardcodar cada numero (validado com dado
    real: assets/finalcial/Financeiro/extrato/1035-.../*.xls)."""
    nome = os.path.basename(caminho_arquivo)
    match = re.search(r"(\d{4})", nome)
    if match:
        return f"Itaú_{match.group(1)}"
    return "Itaú_CC_Cartão"


def _data_iso(valor_bruto) -> str | None:
    """Converte a data da celula do XLS (numero serial do Excel ou texto
    dd/mm/aaaa) para ISO -- mesma logica de para_iso() do script legado."""
    if isinstance(valor_bruto, float) and valor_bruto > 40000:
        try:
            data = xlrd.xldate_as_datetime(valor_bruto, 0)
            return data.strftime("%Y-%m-%d")
        except Exception:
            return None
    texto = str(valor_bruto).strip()
    for formato in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
        try:
            from datetime import datetime

            return datetime.strptime(texto, formato).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def parsear(caminho_arquivo: str) -> list[dict]:
    """Le uma fatura de cartao Itau em .xls e retorna uma lista de
    registros no mesmo formato aceito por
    importar_historico_extrato.processar_transacoes (data, descricao,
    valor_raw, conta, fonte) -- reaproveita a mesma persistencia/
    classificacao/reconciliacao da migracao historica (research.md #10/#11,
    T048), sem duplicar essa logica aqui. Porta os mesmos filtros de
    cabecalho/total/"pagamento efetuado" do script legado."""
    workbook = xlrd.open_workbook(caminho_arquivo)
    planilha = workbook.sheet_by_index(0)
    conta = _conta_pelo_nome_arquivo(caminho_arquivo)
    fonte = os.path.basename(caminho_arquivo)

    registros: list[dict] = []
    for linha in range(planilha.nrows):
        celulas = [planilha.cell_value(linha, coluna) for coluna in range(planilha.ncols)]
        if len(celulas) < 3:
            continue

        data_bruta = celulas[0]
        descricao = str(celulas[1]).strip() if celulas[1] else ""
        valor_bruto = celulas[3] if len(celulas) > 3 else None

        if not descricao or descricao.lower() in _DESCRICOES_IGNORADAS:
            continue
        if str(data_bruta).strip() in ("", "data", "lançamento"):
            continue
        if not isinstance(valor_bruto, (int, float)):
            continue
        if "total" in descricao.lower() or "total" in str(data_bruta).lower():
            continue
        if "pagamento efetuado" in descricao.lower():
            continue

        data_iso = _data_iso(data_bruta)
        if not data_iso:
            continue

        registros.append(
            {
                "data": data_iso,
                "descricao": descricao,
                "valor_raw": float(valor_bruto),
                "conta": conta,
                "fonte": fonte,
                # Todo cartao Itau importado por este parser e do Marcelo --
                # titular fixo, mesmo espirito do parser do extrato BB
                # (feature 011, research.md #7).
                "titular": "marcelo",
            }
        )

    return registros
