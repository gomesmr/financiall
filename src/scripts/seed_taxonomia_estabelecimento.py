from __future__ import annotations

import argparse
import sqlite3
import sys

from src.storage import db as storage_db

# Taxonomia-semente de tipo de estabelecimento (feature 009, US6) -- eixo
# independente da taxonomia de categoria do item (feature 008,
# seed_taxonomia_categorizacao.py), embora compartilhe o mesmo mecanismo de
# categoria de dois niveis (data-model.md). So adiciona o que ainda nao
# existir -- nunca renomeia nem remove categoria ja usada por notas reais
# (research.md #7).
#
# Cada item e (nome de topo, [nomes de subcategoria]) -- lista vazia =
# tipo de estabelecimento sem subcategoria.
TAXONOMIA_ESTABELECIMENTO: list[tuple[str, list[str]]] = [
    ("Supermercado", []),
    ("Mercearia", []),
    ("Restaurante", []),
    ("Bar", []),
    ("Farmácia", []),
    ("Pet Shop", []),
    ("Saúde", ["Dentista", "Plano de Saúde"]),
]


def _normalizar_nome(nome: str) -> str:
    return nome.strip().casefold()


def _obter_ou_criar_categoria(conn: sqlite3.Connection, nome: str, parent_id: int | None) -> int:
    """Mesmo padrao de seed_taxonomia_categorizacao.py (feature 008): insere
    a categoria/subcategoria so se ainda nao existir (por nome_normalizado,
    escopado pelo mesmo nivel dos indices parciais) e retorna o id --
    existente ou recem-criado."""
    nome_limpo = nome.strip()
    nome_normalizado = _normalizar_nome(nome_limpo)
    if parent_id is None:
        row = conn.execute(
            "SELECT id FROM categoria WHERE nome_normalizado = ? AND parent_id IS NULL",
            (nome_normalizado,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT id FROM categoria WHERE nome_normalizado = ? AND parent_id = ?",
            (nome_normalizado, parent_id),
        ).fetchone()
    if row is not None:
        return row["id"]

    cursor = conn.execute(
        "INSERT INTO categoria (nome, nome_normalizado, parent_id) VALUES (?, ?, ?)",
        (nome_limpo, nome_normalizado, parent_id),
    )
    return cursor.lastrowid


def seed_taxonomia_estabelecimento(db_path: str = storage_db.DEFAULT_DB_PATH) -> None:
    """Insere a taxonomia-semente de tipo de estabelecimento em `categoria`
    -- so o que ainda nao existe (por nome_normalizado); chamar de novo nao
    duplica nada, e categorias de estabelecimento ja criadas pelo usuario
    (feature 003) sao preservadas como estao."""
    conn = storage_db.get_connection(db_path)
    try:
        for nome_topo, subcategorias in TAXONOMIA_ESTABELECIMENTO:
            topo_id = _obter_ou_criar_categoria(conn, nome_topo, None)
            for nome_sub in subcategorias:
                _obter_ou_criar_categoria(conn, nome_sub, topo_id)
        conn.commit()
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Semeia a taxonomia-semente de tipo de estabelecimento (feature 009)."
    )
    parser.add_argument("--db-path", dest="db_path", default=storage_db.DEFAULT_DB_PATH, help="Banco de destino")
    args = parser.parse_args(argv)

    storage_db.init_db(args.db_path)
    seed_taxonomia_estabelecimento(db_path=args.db_path)

    print("Taxonomia de tipo de estabelecimento aplicada com sucesso.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
