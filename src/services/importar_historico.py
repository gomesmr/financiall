from __future__ import annotations

import json
import re
from dataclasses import dataclass

from src.models.item_nota import ItemNota
from src.models.nota_fiscal import CanalOrigem, NotaFiscal, StatusNota
from src.storage import db as storage_db

_TITULARES_CONHECIDOS = {"marcelo", "cristine"}
_PADRAO_CHAVE = re.compile(r"^\d{44}$")


class ArquivoHistoricoError(Exception):
    """Arquivo de historico ausente ou nao interpretavel como JSON (FR-007)."""


@dataclass
class ResumoImportacao:
    importadas: int = 0
    ja_existentes: int = 0
    puladas: int = 0


def _chave_valida(chave: object) -> bool:
    return isinstance(chave, str) and _PADRAO_CHAVE.fullmatch(chave) is not None


def _converter_valor(valor: float | int | None) -> int | None:
    """Reais (float) -> centavos (int), research.md #2."""
    if valor is None:
        return None
    return round(valor * 100)


def _converter_data(data_str: str | None) -> str | None:
    """DD/MM/YYYY (historico) -> YYYY-MM-DD (schema atual), research.md #3."""
    if not data_str:
        return None
    partes = data_str.split("/")
    if len(partes) != 3:
        return None
    dia, mes, ano = partes
    if not (dia.isdigit() and mes.isdigit() and ano.isdigit()):
        return None
    return f"{ano}-{mes.zfill(2)}-{dia.zfill(2)}"


def _mapear_titular(conta: object) -> str:
    if isinstance(conta, str) and conta in _TITULARES_CONHECIDOS:
        return conta
    return "nao_identificado"


def _mapear_canal_origem(fonte: object) -> CanalOrigem:
    """research.md #5: 'pdf' -> foto_pdf; 'qr' ou ausente -> url_chave."""
    if fonte == "pdf":
        return CanalOrigem.FOTO_PDF
    return CanalOrigem.URL_CHAVE


def _mapear_item(item_bruto: dict) -> ItemNota:
    vl_liquido = item_bruto.get("vl_liquido")
    vl_total = item_bruto.get("vl_total")
    valor_total_item = _converter_valor(vl_liquido if vl_liquido is not None else vl_total)
    return ItemNota(
        nota_fiscal_id=0,  # ignorado por inserir_nota_com_itens, que usa o id gerado na propria transacao
        codigo_item=item_bruto.get("codigo"),
        descricao=item_bruto.get("descricao"),
        quantidade=item_bruto.get("qtd"),
        valor_unitario=_converter_valor(item_bruto.get("vl_unit")),
        valor_total_item=valor_total_item,
    )


def _mapear_registro(chave: str, dados: dict) -> tuple[NotaFiscal, list[ItemNota]]:
    data_emissao = _converter_data(dados.get("data_emissao"))
    nota = NotaFiscal(
        canal_origem=_mapear_canal_origem(dados.get("fonte")),
        status=StatusNota.COMPLETA,
        chave_acesso=chave,
        cnpj_emitente=dados.get("cnpj"),
        emitente_nome=dados.get("emitente"),
        uf=dados.get("uf"),
        data_emissao=data_emissao,
        ano_mes_emissao=(data_emissao[2:4] + data_emissao[5:7]) if data_emissao else None,
        valor_total=_converter_valor(dados.get("total")),
        titular=_mapear_titular(dados.get("conta")),
    )
    itens = [_mapear_item(item) for item in dados.get("itens") or []]
    return nota, itens


def importar_historico(caminho_arquivo: str, db_path: str = storage_db.DEFAULT_DB_PATH) -> ResumoImportacao:
    """Le o arquivo de historico e grava toda nota que ainda nao existe
    (por chave de acesso), com seus itens. Nunca imprime/loga chave,
    CNPJ, emitente ou valor (Principio IV) -- so retorna contagens."""
    try:
        with open(caminho_arquivo, encoding="utf-8") as arquivo:
            dados_brutos = json.load(arquivo)
    except FileNotFoundError:
        raise ArquivoHistoricoError(f"Arquivo não encontrado: {caminho_arquivo}") from None
    except json.JSONDecodeError:
        raise ArquivoHistoricoError("Não foi possível interpretar o arquivo como JSON válido.") from None

    resumo = ResumoImportacao()
    for chave, registro in dados_brutos.items():
        if not _chave_valida(chave):
            resumo.puladas += 1
            continue

        if storage_db.buscar_por_chave_acesso(chave, db_path=db_path) is not None:
            resumo.ja_existentes += 1
            continue

        nota, itens = _mapear_registro(chave, registro)
        storage_db.inserir_nota_com_itens(nota, itens, db_path=db_path)
        resumo.importadas += 1

    return resumo
