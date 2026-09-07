from __future__ import annotations

import re

from src.models.compromisso_futuro import CompromissoFuturo
from src.storage import db as storage_db

_RE_MES_ISO = re.compile(r"^\d{4}-\d{2}$")


def _somar_meses(mes_iso: str, offset: int) -> str:
    """Soma `offset` meses a um "AAAA-MM" (offset pode ser 0)."""
    ano, mes = (int(parte) for parte in mes_iso.split("-"))
    indice_total = (ano * 12 + (mes - 1)) + offset
    novo_ano, novo_mes = divmod(indice_total, 12)
    return f"{novo_ano:04d}-{novo_mes + 1:02d}"


def validar_e_criar_compromisso(
    descricao: str,
    valor_parcela: int,
    parcela_atual: int,
    total_parcelas: int,
    mes_referencia: str,
    conta: str | None = None,
    titular: str | None = None,
    db_path: str = storage_db.DEFAULT_DB_PATH,
) -> tuple[int | None, str | None]:
    """Valida e cadastra um compromisso futuro. Retorna (id, None) em
    sucesso ou (None, mensagem_erro)."""
    descricao_limpa = (descricao or "").strip()
    if not descricao_limpa:
        return None, "Descrição é obrigatória."
    if not isinstance(valor_parcela, int) or valor_parcela <= 0:
        return None, "Valor da parcela deve ser maior que zero."
    if not isinstance(parcela_atual, int) or parcela_atual < 1:
        return None, "Parcela atual deve ser 1 ou maior."
    if not isinstance(total_parcelas, int) or total_parcelas < parcela_atual:
        return None, "Total de parcelas deve ser maior ou igual à parcela atual."
    if not mes_referencia or not _RE_MES_ISO.match(mes_referencia):
        return None, "Mês de referência inválido (esperado AAAA-MM)."

    compromisso = CompromissoFuturo(
        descricao=descricao_limpa,
        valor_parcela=valor_parcela,
        parcela_atual=parcela_atual,
        total_parcelas=total_parcelas,
        mes_referencia=mes_referencia,
        conta=(conta or "").strip() or None,
        titular=titular or None,
    )
    compromisso_id = storage_db.criar_compromisso_futuro(compromisso, db_path=db_path)
    return compromisso_id, None


def projetar_compromissos_futuros(db_path: str = storage_db.DEFAULT_DB_PATH) -> list[dict]:
    """Retorna a projecao mes a mes de todos os compromissos ativos, do
    mes de referencia mais proximo ate a ultima parcela de cada um.
    Formato: [{"mes": "AAAA-MM", "total": centavos, "itens": [...]}],
    ordenado por mes -- o mesmo formato que resumo_service.
    agrupar_transacoes_por_mes usa para as listagens existentes, para a
    template poder reaproveitar o mesmo padrao de exibicao."""
    compromissos = storage_db.listar_compromissos_futuros(apenas_ativos=True, db_path=db_path)

    por_mes: dict[str, dict] = {}
    for compromisso in compromissos:
        parcelas_restantes = compromisso.total_parcelas - compromisso.parcela_atual + 1
        for offset in range(parcelas_restantes):
            mes = _somar_meses(compromisso.mes_referencia, offset)
            numero_parcela = compromisso.parcela_atual + offset
            grupo = por_mes.setdefault(mes, {"mes": mes, "total": 0, "itens": []})
            grupo["total"] += compromisso.valor_parcela
            grupo["itens"].append(
                {
                    "descricao": compromisso.descricao,
                    "conta": compromisso.conta,
                    "titular": compromisso.titular,
                    "valor": compromisso.valor_parcela,
                    "parcela": f"{numero_parcela}/{compromisso.total_parcelas}",
                }
            )

    return [por_mes[mes] for mes in sorted(por_mes)]
