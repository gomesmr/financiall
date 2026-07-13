from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.storage import db as storage_db


@dataclass(frozen=True)
class ResumoMes:
    mes: str
    total_gasto: int | None
    quantidade_notas: int


def mes_atual() -> str:
    hoje = date.today()
    return f"{hoje.year:04d}-{hoje.month:02d}"


def _query_resumo_por_mes(db_path: str) -> list[ResumoMes]:
    """Agrupa as notas por mês (data_emissao, com fallback para
    ano_mes_emissao decodificado da chave), somando valor_total em
    centavos — SQLite ignora nulos em SUM automaticamente — e contando
    todas as notas do mês, inclusive as pendentes de revisão (FR-015/016)."""
    conn = storage_db.get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT
                COALESCE(substr(data_emissao, 1, 7), '20' || substr(ano_mes_emissao, 1, 2) || '-' || substr(ano_mes_emissao, 3, 2)) AS mes,
                SUM(valor_total) AS total_gasto,
                COUNT(*) AS quantidade_notas
            FROM nota_fiscal
            WHERE COALESCE(substr(data_emissao, 1, 7), '20' || substr(ano_mes_emissao, 1, 2) || '-' || substr(ano_mes_emissao, 3, 2)) IS NOT NULL
            GROUP BY mes
            ORDER BY mes DESC
            """
        ).fetchall()
        return [
            ResumoMes(mes=row["mes"], total_gasto=row["total_gasto"], quantidade_notas=row["quantidade_notas"])
            for row in rows
        ]
    finally:
        conn.close()


def gasto_mes_corrente(db_path: str = storage_db.DEFAULT_DB_PATH) -> ResumoMes | None:
    """Total parcial do mês corrente (US7, FR-015). None se não há
    nenhuma nota com data no mês corrente."""
    mes = mes_atual()
    for resumo in _query_resumo_por_mes(db_path):
        if resumo.mes == mes:
            return resumo
    return None


def historico_meses_anteriores(db_path: str = storage_db.DEFAULT_DB_PATH) -> list[ResumoMes]:
    """Total por mês para meses anteriores ao corrente (US8, FR-016),
    ordenado do mais recente para o mais antigo."""
    mes = mes_atual()
    return [resumo for resumo in _query_resumo_por_mes(db_path) if resumo.mes < mes]
