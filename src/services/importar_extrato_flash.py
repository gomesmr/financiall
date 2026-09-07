from __future__ import annotations

import csv
import os
from datetime import datetime

# Todo arquivo desta pasta pertence ao mesmo beneficio Flash (vale-
# alimentacao/refeicao) do Marcelo -- titular fixo, mesmo espirito do
# parser do extrato BB (research.md #7 da feature 011).
TITULAR = "marcelo"
CONTA = "Flash"


def _data_iso(valor_bruto: str) -> str | None:
    texto = valor_bruto.strip()
    if not texto:
        return None
    try:
        return datetime.strptime(texto, "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def _valor_float(valor_bruto: str) -> float | None:
    """Extrato do Flash traz o valor como texto com prefixo 'R$' e formato
    BR (milhar com ponto, decimal com virgula, ex.: '-R$ 1.234,56') -- o
    espaco entre 'R$' e o numero costuma ser um NBSP (\\xa0), nao um espaco
    comum, por isso o replace explicito abaixo alem do " " (achado
    processando o CSV real: um valor negativo como '-R$\\xa072,00' vira
    '-\\xa072,00' apos remover 'R$', com o NBSP sanduichado entre o sinal e
    o digito -- float() so ignora espaco em branco no inicio/fim da
    string, nao no meio, entao sem essa limpeza todo valor negativo
    falhava silenciosamente)."""
    texto = (
        valor_bruto.strip()
        .replace("R$", "")
        .replace("\xa0", "")
        .replace(" ", "")
        .replace(".", "")
        .replace(",", ".")
    )
    if not texto:
        return None
    try:
        return float(texto)
    except ValueError:
        return None


def parsear(caminho_arquivo: str) -> list[dict]:
    """Le um extrato do Flash (.csv, colunas Data/Hora/Movimentacao/Valor/
    Meio de Pagamento/Saldo) e retorna uma lista de registros no mesmo
    formato aceito por importar_historico_extrato.processar_transacoes.
    O sinal do valor aqui ja vem correto no arquivo, mas
    _interpretar_valor_e_tipo trata conta "flash" de forma especial
    (direcao pela descricao, nao pelo sinal) -- mesma convencao do dado
    legado que ja existe no banco, entao nao precisa de tratamento
    diferente aqui."""
    fonte = os.path.basename(caminho_arquivo)

    registros: list[dict] = []
    with open(caminho_arquivo, encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        for linha in leitor:
            data_iso = _data_iso(linha.get("Data") or "")
            descricao = (linha.get("Movimentação") or "").strip()
            valor = _valor_float(linha.get("Valor") or "")

            if not data_iso or not descricao or valor is None:
                continue

            registros.append(
                {
                    "data": data_iso,
                    "descricao": descricao,
                    "valor_raw": valor,
                    "conta": CONTA,
                    "fonte": fonte,
                    "titular": TITULAR,
                }
            )

    return registros
