from __future__ import annotations

import re

from src.services.normalizacao import normalizar_descricao
from src.storage import db as storage_db


def classificar_natureza(
    descricao: str | None, db_path: str = storage_db.DEFAULT_DB_PATH
) -> tuple[str | None, int | None, str | None]:
    """Cascata de classificacao automatica de natureza (research.md #6),
    espelhando classificacao_itens.classificar_item: cache (Tier 1) ->
    regra ativa mais especifica (Tier 2) -> (None, None, None) (Tier 3,
    pendente). Descricao None/vazia vai direto para pendente, mesmo padrao
    do caso equivalente para item."""
    if not descricao or not descricao.strip():
        return None, None, None

    descricao_normalizada = normalizar_descricao(descricao)
    if not descricao_normalizada:
        return None, None, None

    conn = storage_db.get_connection(db_path)
    try:
        linha_cache = conn.execute(
            "SELECT natureza, categoria_id FROM cache_descricao_natureza WHERE descricao_normalizada = ?",
            (descricao_normalizada,),
        ).fetchone()
        if linha_cache is not None:
            return linha_cache["natureza"], linha_cache["categoria_id"], "cache"

        regras = conn.execute(
            "SELECT padrao, natureza, categoria_id FROM regra_natureza WHERE ativa = 1 ORDER BY prioridade DESC, id ASC"
        ).fetchall()
    finally:
        conn.close()

    for regra in regras:
        padrao = re.escape(regra["padrao"])
        if re.search(rf"\b{padrao}\b", descricao_normalizada):
            return regra["natureza"], regra["categoria_id"], "regra"

    return None, None, None
