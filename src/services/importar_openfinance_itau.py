from __future__ import annotations

import datetime
import json
import os

# Margem entre o inicio da janela pedida e o corte real de filtragem de
# parcela antiga (ver _parsear_cartoes) -- generosa o bastante pra nao
# descartar compra legitima perto da borda da janela (o ciclo da fatura do
# cartao raramente alinha exatamente com a data pedida: uma fatura que
# fecha poucos dias antes do "from_date" ainda traz compras legitimas de
# alguns dias antes dele), mas curta o bastante pra pegar o caso real
# encontrado com dado real (parcela de uma compra de mais de um ano atras
# reaparecendo com a data de compra original em toda fatura nova).
_MARGEM_DIAS_JANELA_CARTAO = 40

# A conta corrente reaproveita a mesma grafia do parser manual
# (importar_extrato_itau_cc.py) para canonicalizar para "itau_cc" -- sem
# isso, o Open Finance criaria uma conta paralela para o mesmo dinheiro
# real, quebrando a continuidade dos relatorios.
_CONTA_CORRENTE = "Itaú_CC"

# Poupanca nao tem parser manual equivalente. Evita o prefixo "itau_" de
# proposito: conta_canonica._eh_conta_cartao() trata qualquer
# "itau_<algo>" que nao termine em "_cc" como cartao de credito (heuristica
# de sinal), o que inverteria entrada/saida numa conta que na verdade segue
# a convencao padrao (positivo=entrada, negativo=saida).
_CONTA_POUPANCA = "poupanca_itau"

# Descricoes que representam o pagamento da fatura aparecendo do lado do
# proprio cartao (credito no extrato do cartao) -- o mesmo evento ja e
# capturado do lado da conta corrente como "Pagamento de fatura ..."
# (mesmo espirito do filtro "pagamento efetuado" em
# importar_extrato_itau_cartao.py). Sem esse filtro, o pagamento da fatura
# seria contado duas vezes.
_DESCRICOES_PAGAMENTO_FATURA = {"pagamento com saldo"}


def _data_iso(transaction_date_time: str) -> str:
    return transaction_date_time[:10]


def _data_corte_parcela_antiga(data_minima: str) -> str:
    data = datetime.date.fromisoformat(data_minima) - datetime.timedelta(days=_MARGEM_DIAS_JANELA_CARTAO)
    return data.isoformat()


def _parsear_contas(dados_contas: dict, fonte: str) -> list[dict]:
    registros: list[dict] = []
    for conta_info in dados_contas.values():
        tipo_conta = conta_info.get("type")
        conta = _CONTA_CORRENTE if tipo_conta == "CONTA_DEPOSITO_A_VISTA" else _CONTA_POUPANCA
        for transacao in conta_info.get("transactions", []):
            valor_abs = float(transacao["transactionAmount"]["amount"])
            valor_raw = valor_abs if transacao["creditDebitType"] == "CREDITO" else -valor_abs
            registros.append(
                {
                    "data": _data_iso(transacao["transactionDateTime"]),
                    "descricao": transacao["transactionName"],
                    "valor_raw": valor_raw,
                    "conta": conta,
                    "fonte": fonte,
                    "titular": "marcelo",
                }
            )
    return registros


def _parsear_cartoes(dados_cartoes: dict, fonte: str, data_minima: str | None) -> list[dict]:
    registros: list[dict] = []
    for cartao_info in dados_cartoes.values():
        for transacao in cartao_info.get("bill_transactions", []):
            descricao = transacao["transactionName"]
            if descricao.strip().lower() in _DESCRICOES_PAGAMENTO_FATURA:
                continue

            data_iso = _data_iso(transacao["transactionDateTime"])
            if data_minima and data_iso < _data_corte_parcela_antiga(data_minima):
                # Parcela em andamento de uma compra antiga (ex.: 16/21):
                # a API do Open Finance mantem a data da COMPRA ORIGINAL em
                # transactionDateTime em vez da data desta parcela
                # especifica -- sem esse filtro, cada parcela mensal futura
                # criaria uma transacao nova com a mesma data antiga (so a
                # descricao muda, "16/21" -> "17/21"), empilhando gasto
                # datado de mais de um ano atras a cada importacao
                # recorrente. A parcela em si so entra quando cai dentro da
                # janela pedida (o que nunca acontece pra parcelas de
                # compras antigas ao Open Finance -- limitacao conhecida,
                # documentada para o usuario).
                continue

            valor_abs = float(transacao["amount"]["amount"])
            # Cartao: positivo = compra (saida), negativo = estorno/credito
            # (entrada) -- convencao oposta a conta corrente, ver
            # _interpretar_valor_e_tipo em importar_historico_extrato.py.
            valor_raw = valor_abs if transacao["creditDebitType"] == "DEBITO" else -valor_abs
            identificacao = transacao.get("identificationNumber", "")
            conta = f"Itaú_{identificacao}" if identificacao else "Itaú_CC_Cartão"

            registros.append(
                {
                    "data": data_iso,
                    "descricao": descricao,
                    "valor_raw": valor_raw,
                    "conta": conta,
                    "fonte": fonte,
                    "titular": "marcelo",
                }
            )
    return registros


def parsear(caminho_arquivo: str) -> list[dict]:
    """Le um dump JSON de dados do Open Finance Itau (contas + faturas de
    cartao, buscados via MCP cumbuca-openfinance) e retorna uma lista de
    registros no formato aceito por
    importar_historico_extrato.processar_transacoes. O app nao tem acesso
    direto ao MCP -- o dump e gerado por uma sessao do Claude que chamou as
    tools do MCP e salvou o resultado bruto neste formato (ver
    assets/openfinance/*.json, fora do controle de versao por conter dado
    financeiro real)."""
    with open(caminho_arquivo, encoding="utf-8") as arquivo:
        dados = json.load(arquivo)

    fonte = os.path.basename(caminho_arquivo)
    data_minima = dados.get("from_date")
    registros = _parsear_contas(dados.get("accounts", {}), fonte)
    registros += _parsear_cartoes(dados.get("credit_cards", {}), fonte, data_minima)
    return registros
