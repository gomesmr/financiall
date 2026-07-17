from __future__ import annotations

import re

from src.services.normalizacao import normalizar_descricao
from src.storage import db as storage_db


def classificar_item(
    descricao: str | None, db_path: str = storage_db.DEFAULT_DB_PATH
) -> tuple[int | None, str | None]:
    """Cascata de classificacao automatica (research.md #8): cache
    (Tier 1) -> regra ativa mais especifica (Tier 2) -> (None, None)
    (Tier 3, pendente). Descricao None/vazia (apos strip()) vai direto
    para pendente, sem tentar normalizar nem casar cache/regra
    (research.md #20)."""
    if not descricao or not descricao.strip():
        return None, None

    descricao_normalizada = normalizar_descricao(descricao)
    if not descricao_normalizada:
        return None, None

    conn = storage_db.get_connection(db_path)
    try:
        linha_cache = conn.execute(
            "SELECT categoria_id FROM cache_descricao_categoria WHERE descricao_normalizada = ?",
            (descricao_normalizada,),
        ).fetchone()
        if linha_cache is not None:
            return linha_cache["categoria_id"], "cache"

        regras = conn.execute(
            "SELECT padrao, categoria_id FROM regra_categoria WHERE ativa = 1 ORDER BY prioridade DESC, id ASC"
        ).fetchall()
    finally:
        conn.close()

    for regra in regras:
        padrao = re.escape(regra["padrao"])
        if re.search(rf"\b{padrao}\b", descricao_normalizada):
            return regra["categoria_id"], "regra"

    return None, None


def classificar_itens_pendentes_da_nota(nota_fiscal_id: int, db_path: str = storage_db.DEFAULT_DB_PATH) -> None:
    """Aplica `classificar_item` a todo `item_nota` com `categoria_id IS
    NULL` da nota informada (research.md #8) -- idempotente por
    construcao: reprocessar uma nota ja classificada nao reclassifica nem
    duplica nada, ja que so seleciona itens ainda pendentes. Mesmo quando
    a cascata nao resolve (Tier 3), a descricao normalizada e persistida
    para a fila de pendentes poder agrupar por ela (T013)."""
    conn = storage_db.get_connection(db_path)
    try:
        itens = conn.execute(
            "SELECT id, descricao FROM item_nota WHERE nota_fiscal_id = ? AND categoria_id IS NULL",
            (nota_fiscal_id,),
        ).fetchall()
    finally:
        conn.close()

    for item in itens:
        categoria_id, metodo = classificar_item(item["descricao"], db_path=db_path)
        descricao_normalizada = normalizar_descricao(item["descricao"])

        if categoria_id is not None:
            storage_db.classificar_item_automaticamente(
                item["id"], categoria_id, metodo, descricao_normalizada, db_path=db_path
            )
        elif descricao_normalizada:
            storage_db.definir_descricao_normalizada_item(item["id"], descricao_normalizada, db_path=db_path)


def obter_evolucao_classificacao(db_path: str = storage_db.DEFAULT_DB_PATH) -> dict:
    """Duas series cumulativas para o grafico de evolucao/burndown
    (research.md #22, T018): "itens totais" -- um ponto por evento de
    importacao de nota (`nota_fiscal.data_importacao`), somando os itens
    que aquela nota trouxe -- e "itens classificados" -- um ponto por
    item na primeira vez que aparece em `historico_classificacao_item`
    (menor `timestamp` por `item_nota_id`). Consulta propria (mesmo
    padrao de `services/resumo.py`), nao delegada a `storage/db.py` por
    ser leitura agregada de relatorio, nao CRUD de repositorio."""
    conn = storage_db.get_connection(db_path)
    try:
        linhas_totais = conn.execute(
            """
            SELECT nota_fiscal.data_importacao AS timestamp, COUNT(item_nota.id) AS quantidade
            FROM nota_fiscal
            LEFT JOIN item_nota ON item_nota.nota_fiscal_id = nota_fiscal.id
            GROUP BY nota_fiscal.id
            ORDER BY nota_fiscal.data_importacao ASC
            """
        ).fetchall()

        linhas_classificados = conn.execute(
            """
            SELECT MIN(timestamp) AS timestamp
            FROM historico_classificacao_item
            GROUP BY item_nota_id
            ORDER BY timestamp ASC
            """
        ).fetchall()
    finally:
        conn.close()

    itens_totais = []
    acumulado = 0
    for linha in linhas_totais:
        acumulado += linha["quantidade"]
        itens_totais.append({"timestamp": linha["timestamp"], "total": acumulado})

    itens_classificados = []
    acumulado = 0
    for linha in linhas_classificados:
        acumulado += 1
        itens_classificados.append({"timestamp": linha["timestamp"], "total": acumulado})

    return {"itens_totais": itens_totais, "itens_classificados": itens_classificados}
