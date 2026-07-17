from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from src.storage import db as storage_db

# Taxonomia definitiva (Tarefa 1 / T001), a partir do rascunho em
# assets/files.zip/taxonomia-v1-rascunho.md, com os pontos em aberto
# decididos: sem categoria/subcategoria fallback "Outros" em lugar nenhum
# (research.md #17); Limpeza doméstica plana, sem subcategorias; Bebidas
# alcoólicas como categoria de topo própria, separada de Bebidas; Bebê e
# Pet como categorias de topo próprias (recomendação do rascunho).
#
# Cada item é (nome da categoria de topo, [nomes de subcategoria]) --
# lista vazia = categoria de topo sem subcategoria (classificação sempre
# parcial, FR-011).

TAXONOMIA_NOTA: list[tuple[str, list[str]]] = [
    (
        "Alimentação",
        [
            "Hortifruti",
            "Carnes e aves",
            "Peixes e frutos do mar",
            "Frios e laticínios",
            "Padaria",
            "Mercearia seca",
            "Matinais e doces",
            "Congelados",
            "Snacks",
        ],
    ),
    ("Bebidas", []),
    ("Alcoólicas", []),
    ("Limpeza doméstica", []),
    (
        "Higiene pessoal e perfumaria",
        ["Papel higiênico", "Cabelo", "Bucal", "Corpo e banho", "Absorvente/íntimo"],
    ),
    (
        "Saúde / medicamentos",
        ["Medicamento", "Vitaminas e suplementos", "Primeiros socorros"],
    ),
    ("Beleza / dermocosméticos", []),
    ("Bebê / infantil", ["Fralda", "Alimentação infantil"]),
    ("Pet", ["Ração", "Petisco", "Higiene animal"]),
    ("Casa / bazar / utilidades", []),
]

# Reservadas para o extrato bancário (fora do escopo de classificação
# desta feature) -- criadas já para não fragmentar a taxonomia depois,
# mas nenhuma regra/cache desta feature aponta para elas.
TAXONOMIA_RESERVADA_EXTRATO: list[tuple[str, list[str]]] = [
    ("Moradia", ["Aluguel", "Contas de consumo"]),
    ("Transporte", ["Combustível", "Transporte público", "Apps de mobilidade"]),
    ("Educação", []),
    ("Lazer", []),
    ("Serviços e assinaturas", []),
    ("Vestuário", []),
    ("Finanças", ["Tarifas e juros", "Entradas/renda"]),
]

# Regras-semente (padrao -> categoria/subcategoria) -- inicialmente
# vazio/minimo (T007); curado a partir do corpus real na T030 (US3).
REGRAS_SEMENTE_PATH = Path(__file__).parent / "regras_semente_categorizacao.json"


def _normalizar_nome(nome: str) -> str:
    return nome.strip().casefold()


def _obter_ou_criar_categoria(conn: sqlite3.Connection, nome: str, parent_id: int | None) -> int:
    """Insere a categoria/subcategoria se ainda nao existir (por
    nome_normalizado, escopado pelo mesmo nivel dos indices parciais --
    research.md #19) e retorna o id -- existente ou recem-criado."""
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


def seed_taxonomia(db_path: str = storage_db.DEFAULT_DB_PATH) -> None:
    """Insere a taxonomia definitiva em `categoria` -- so o que ainda nao
    existe (por nome_normalizado); chamar de novo nao duplica nada."""
    conn = storage_db.get_connection(db_path)
    try:
        for taxonomia in (TAXONOMIA_NOTA, TAXONOMIA_RESERVADA_EXTRATO):
            for nome_topo, subcategorias in taxonomia:
                topo_id = _obter_ou_criar_categoria(conn, nome_topo, None)
                for nome_sub in subcategorias:
                    _obter_ou_criar_categoria(conn, nome_sub, topo_id)
        conn.commit()
    finally:
        conn.close()


def _resolver_categoria_id(conn: sqlite3.Connection, categoria: str, subcategoria: str | None) -> int:
    row_topo = conn.execute(
        "SELECT id FROM categoria WHERE nome_normalizado = ? AND parent_id IS NULL",
        (_normalizar_nome(categoria),),
    ).fetchone()
    if row_topo is None:
        raise ValueError(f"Categoria de topo '{categoria}' não encontrada na taxonomia semeada.")

    if not subcategoria:
        return row_topo["id"]

    row_sub = conn.execute(
        "SELECT id FROM categoria WHERE nome_normalizado = ? AND parent_id = ?",
        (_normalizar_nome(subcategoria), row_topo["id"]),
    ).fetchone()
    if row_sub is None:
        raise ValueError(f"Subcategoria '{subcategoria}' não encontrada sob '{categoria}'.")
    return row_sub["id"]


def seed_regras(db_path: str = storage_db.DEFAULT_DB_PATH) -> None:
    """Le o arquivo de regras-semente (JSON, inicialmente vazio) e insere
    em `regra_categoria` -- so o que ainda nao existe (por padrao +
    categoria_id); chamar de novo nao duplica nada. Depende da taxonomia
    ja semeada (seed_taxonomia) para resolver categoria/subcategoria pelo
    nome."""
    if not REGRAS_SEMENTE_PATH.exists():
        return

    with open(REGRAS_SEMENTE_PATH, encoding="utf-8") as arquivo:
        regras = json.load(arquivo)

    conn = storage_db.get_connection(db_path)
    try:
        for regra in regras:
            categoria_id = _resolver_categoria_id(conn, regra["categoria"], regra.get("subcategoria"))
            padrao = regra["padrao"].strip().upper()
            prioridade = regra.get("prioridade", 0)

            existe = conn.execute(
                "SELECT 1 FROM regra_categoria WHERE padrao = ? AND categoria_id = ?",
                (padrao, categoria_id),
            ).fetchone()
            if existe is not None:
                continue

            conn.execute(
                "INSERT INTO regra_categoria (padrao, categoria_id, prioridade, ativa) VALUES (?, ?, ?, 1)",
                (padrao, categoria_id, prioridade),
            )
        conn.commit()
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Semeia a taxonomia definitiva e as regras-semente de categorização de itens."
    )
    parser.add_argument("--db-path", dest="db_path", default=storage_db.DEFAULT_DB_PATH, help="Banco de destino")
    args = parser.parse_args(argv)

    storage_db.init_db(args.db_path)
    seed_taxonomia(db_path=args.db_path)
    seed_regras(db_path=args.db_path)

    print("Taxonomia e regras-semente aplicadas com sucesso.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
