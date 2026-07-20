from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from src.storage import db as storage_db

REGRAS_SEMENTE_PATH = Path(__file__).parent / "regras_semente_natureza.json"


def _normalizar_nome(nome: str) -> str:
    return nome.strip().casefold()


def _resolver_categoria_id(conn: sqlite3.Connection, categoria: str, subcategoria: str | None) -> int:
    """Resolve categoria/subcategoria contra a taxonomia ja semeada por
    seed_taxonomia_categorizacao.py (inclusive TAXONOMIA_RESERVADA_EXTRATO,
    research.md #4) -- nao cria categoria nova, so mapeia."""
    row_topo = conn.execute(
        "SELECT id FROM categoria WHERE nome_normalizado = ? AND parent_id IS NULL",
        (_normalizar_nome(categoria),),
    ).fetchone()
    if row_topo is None:
        raise ValueError(f"Categoria de topo '{categoria}' não encontrada — rode seed_taxonomia_categorizacao primeiro.")

    if not subcategoria:
        return row_topo["id"]

    row_sub = conn.execute(
        "SELECT id FROM categoria WHERE nome_normalizado = ? AND parent_id = ?",
        (_normalizar_nome(subcategoria), row_topo["id"]),
    ).fetchone()
    if row_sub is None:
        raise ValueError(f"Subcategoria '{subcategoria}' não encontrada sob '{categoria}'.")
    return row_sub["id"]


def seed_regras_natureza(db_path: str = storage_db.DEFAULT_DB_PATH) -> int:
    """Le regras_semente_natureza.json (research.md #5) e insere em
    regra_natureza -- so o que ainda nao existe (por padrao + natureza);
    chamar de novo nao duplica nada. Retorna a quantidade de regras
    inseridas nesta execucao."""
    if not REGRAS_SEMENTE_PATH.exists():
        return 0

    with open(REGRAS_SEMENTE_PATH, encoding="utf-8") as arquivo:
        regras = json.load(arquivo)

    conn = storage_db.get_connection(db_path)
    inseridas = 0
    try:
        for regra in regras:
            natureza = regra["natureza"]
            categoria_id = None
            if natureza == "gasto" and regra.get("categoria"):
                categoria_id = _resolver_categoria_id(conn, regra["categoria"], regra.get("subcategoria"))

            padrao = regra["padrao"].strip().upper()
            prioridade = regra.get("prioridade", 0)

            existe = conn.execute(
                "SELECT 1 FROM regra_natureza WHERE padrao = ? AND natureza = ?",
                (padrao, natureza),
            ).fetchone()
            if existe is not None:
                continue

            conn.execute(
                "INSERT INTO regra_natureza (padrao, natureza, categoria_id, prioridade, ativa) VALUES (?, ?, ?, ?, 1)",
                (padrao, natureza, categoria_id, prioridade),
            )
            inseridas += 1
        conn.commit()
    finally:
        conn.close()
    return inseridas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Semeia as regras-semente de classificação de natureza de transação.")
    parser.add_argument("--db-path", dest="db_path", default=storage_db.DEFAULT_DB_PATH, help="Banco de destino")
    args = parser.parse_args(argv)

    storage_db.init_db(args.db_path)
    seed_regras_natureza(db_path=args.db_path)

    print("Regras-semente de natureza aplicadas com sucesso.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
