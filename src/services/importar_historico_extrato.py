from __future__ import annotations

import json
from dataclasses import dataclass

from src.models.transacao import Transacao, TipoTransacao
from src.services import classificacao_natureza, reconciliacao
from src.services.conta_canonica import canonicalizar_conta
from src.services.fingerprint_transacao import calcular_fingerprint
from src.services.normalizacao import normalizar_descricao
from src.storage import db as storage_db


class ArquivoExtratoError(Exception):
    """Arquivo de extrato ausente ou ilegivel -- aborta a importacao
    inteira sem gravar nada parcial (FR-024)."""


@dataclass
class ImportarExtratoResumo:
    importadas: int = 0
    ja_existentes: int = 0
    puladas: int = 0
    classificadas_automaticamente: int = 0
    pendentes_natureza: int = 0
    reconciliadas: int = 0
    ambiguas: int = 0


def _eh_conta_cartao(conta_canonica: str) -> bool:
    """Cartao de credito Itau (o unico emissor no dado real hoje) -- usado
    tanto pra interpretar o sinal legado quanto pela heuristica de
    estorno/credito."""
    return conta_canonica.startswith("itau_") and not conta_canonica.endswith("_cc")


def _interpretar_valor_e_tipo(conta_canonica: str, valor_raw: float, descricao: str) -> tuple[int, str]:
    """A convencao de sinal do valor bruto do legado depende do tipo de
    conta (mesmo racional de classificar() no script legado): cartao ->
    positivo=compra(saida), negativo=estorno(entrada); conta corrente ->
    positivo=entrada, negativo=saida; Flash -> sempre positivo no dado
    bruto, direcao vem da descricao ('Deposito' = entrada, resto = saida),
    pois o extrato de origem nunca teve sinal."""
    valor_centavos = int(round(abs(valor_raw) * 100))
    if conta_canonica.endswith("_cc"):
        tipo = "entrada" if valor_raw >= 0 else "saida"
    elif conta_canonica == "flash":
        tipo = "entrada" if "DEPOSITO" in normalizar_descricao(descricao) else "saida"
    elif _eh_conta_cartao(conta_canonica):
        tipo = "saida" if valor_raw >= 0 else "entrada"
    else:
        tipo = "entrada" if valor_raw >= 0 else "saida"
    return valor_centavos, tipo


def _classificar_com_heuristica_estorno(
    descricao: str, conta_canonica: str, tipo: str, db_path: str
) -> tuple[str | None, int | None, str | None]:
    """A cascata cache/regra (US1) resolve a maioria; quando nao resolve e
    a transacao e uma entrada de cartao, a natureza mais provavel e
    estorno/credito de uma compra anterior (nunca renda) -- heuristica de
    conta, nao de descricao, por isso um metodo proprio em vez de 'regra'."""
    natureza, categoria_id, metodo = classificacao_natureza.classificar_natureza(descricao, db_path=db_path)
    if natureza is None and tipo == "entrada" and _eh_conta_cartao(conta_canonica):
        return "estorno_credito", None, "heuristica_conta"
    return natureza, categoria_id, metodo


def processar_transacoes(
    registros: list[dict], db_path: str = storage_db.DEFAULT_DB_PATH
) -> ImportarExtratoResumo:
    """Persiste uma lista de transacoes ja normalizadas -- reaproveitada
    tanto pela migracao historica (US2) quanto pelo parser recorrente
    (US6, T048), para nao duplicar fingerprint/classificacao/reconciliacao
    entre os dois pipelines. Cada dict de entrada: {"data" (ISO),
    "descricao", "valor_raw" (com sinal, str ou float), "conta" (grafia
    original), "fonte", "titular"}."""
    resumo = ImportarExtratoResumo()

    for registro in registros:
        data_iso = registro.get("data")
        descricao = registro.get("descricao")
        valor_raw = registro.get("valor_raw")
        conta_raw = registro.get("conta")

        if not data_iso or not descricao or valor_raw in (None, "") or not conta_raw:
            resumo.puladas += 1
            continue

        try:
            valor_float = float(valor_raw)
        except (TypeError, ValueError):
            resumo.puladas += 1
            continue

        conta_canonica = canonicalizar_conta(conta_raw)
        valor_centavos, tipo = _interpretar_valor_e_tipo(conta_canonica, valor_float, descricao)
        fingerprint = calcular_fingerprint(data_iso, descricao, valor_centavos, conta_canonica)

        ja_existia = storage_db.buscar_transacao_por_fingerprint(fingerprint, db_path=db_path) is not None

        descricao_normalizada = normalizar_descricao(descricao) or None
        natureza, categoria_id, metodo = _classificar_com_heuristica_estorno(
            descricao, conta_canonica, tipo, db_path=db_path
        )

        transacao = Transacao(
            fingerprint=fingerprint,
            data=data_iso,
            descricao=descricao,
            descricao_normalizada=descricao_normalizada,
            valor=valor_centavos,
            tipo=TipoTransacao(tipo),
            natureza=natureza,
            metodo_classificacao_natureza=metodo,
            categoria_id=categoria_id,
            conta=conta_canonica,
            titular=registro.get("titular"),
            fonte=registro.get("fonte"),
        )
        transacao_id = storage_db.inserir_transacao(transacao, db_path=db_path)

        if ja_existia:
            resumo.ja_existentes += 1
            continue

        resumo.importadas += 1
        if natureza is not None:
            resumo.classificadas_automaticamente += 1
        else:
            resumo.pendentes_natureza += 1

        if natureza == "gasto":
            resultado = reconciliacao.tentar_reconciliar(transacao_id, conta_canonica, db_path=db_path)
            if resultado == "reconciliada":
                resumo.reconciliadas += 1
            elif resultado == "ambigua":
                resumo.ambiguas += 1

    return resumo


def importar_historico_extrato(
    caminho_arquivo: str, db_path: str = storage_db.DEFAULT_DB_PATH
) -> ImportarExtratoResumo:
    """US2: le o registro.json ja processado pelo script legado
    (importar_extrato.py) e importa as transacoes para a base unica
    (FR-008/FR-009). Arquivo ausente ou JSON invalido aborta tudo, sem
    gravar dado parcial (FR-024)."""
    try:
        with open(caminho_arquivo, encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
    except FileNotFoundError:
        raise ArquivoExtratoError(f"Arquivo não encontrado: {caminho_arquivo}") from None
    except json.JSONDecodeError:
        raise ArquivoExtratoError("Não foi possível interpretar o arquivo como JSON válido.") from None

    registros = [
        {
            "data": item.get("data"),
            "descricao": item.get("desc"),
            "valor_raw": item.get("valor"),
            "conta": item.get("conta"),
            "fonte": item.get("fonte"),
            "titular": item.get("titular"),
        }
        for item in dados.values()
    ]
    return processar_transacoes(registros, db_path=db_path)
