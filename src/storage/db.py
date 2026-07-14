from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path

from src.models.item_nota import ItemNota
from src.models.nota_fiscal import CanalOrigem, NotaFiscal, StatusNota

DEFAULT_DB_PATH = os.environ.get("FINANCIALL_DB_PATH", "data/financiall.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS nota_fiscal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave_acesso TEXT,
    hash_conteudo TEXT,
    canal_origem TEXT NOT NULL CHECK (canal_origem IN ('url_chave', 'foto_pdf')),
    uf TEXT,
    cnpj_emitente TEXT,
    ano_mes_emissao TEXT,
    modelo TEXT,
    emitente_nome TEXT,
    data_emissao TEXT,
    valor_total INTEGER,
    status TEXT NOT NULL CHECK (status IN ('completa', 'pendente_revisao')),
    data_importacao TEXT NOT NULL,
    CHECK (chave_acesso IS NOT NULL OR hash_conteudo IS NOT NULL)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_nota_fiscal_chave_acesso
    ON nota_fiscal(chave_acesso) WHERE chave_acesso IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_nota_fiscal_hash_conteudo
    ON nota_fiscal(hash_conteudo) WHERE hash_conteudo IS NOT NULL;

CREATE TABLE IF NOT EXISTS item_nota (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nota_fiscal_id INTEGER NOT NULL REFERENCES nota_fiscal(id),
    codigo_item TEXT,
    descricao TEXT,
    quantidade REAL,
    valor_unitario INTEGER,
    valor_total_item INTEGER
);

CREATE TABLE IF NOT EXISTS envio_ocr (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    caminho_arquivo TEXT NOT NULL,
    tipo_arquivo TEXT NOT NULL CHECK (tipo_arquivo IN ('foto', 'pdf')),
    hash_conteudo TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pendente', 'processando', 'concluido')) DEFAULT 'pendente',
    nota_fiscal_id INTEGER REFERENCES nota_fiscal(id),
    data_envio TEXT NOT NULL,
    data_processamento TEXT
);
"""


def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Abre uma nova conexao SQLite. Cada operacao de repositorio abre/fecha
    a sua propria conexao (sem estado compartilhado entre threads), o
    suficiente para o volume de uso pessoal desta feature (Principio I)."""
    parent = Path(db_path).parent
    if str(parent) not in ("", "."):
        parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def _row_to_nota(row: sqlite3.Row) -> NotaFiscal:
    return NotaFiscal(
        canal_origem=CanalOrigem(row["canal_origem"]),
        status=StatusNota(row["status"]),
        id=row["id"],
        chave_acesso=row["chave_acesso"],
        hash_conteudo=row["hash_conteudo"],
        uf=row["uf"],
        cnpj_emitente=row["cnpj_emitente"],
        ano_mes_emissao=row["ano_mes_emissao"],
        modelo=row["modelo"],
        emitente_nome=row["emitente_nome"],
        data_emissao=row["data_emissao"],
        valor_total=row["valor_total"],
        data_importacao=row["data_importacao"],
    )


def _row_to_item(row: sqlite3.Row) -> ItemNota:
    return ItemNota(
        id=row["id"],
        nota_fiscal_id=row["nota_fiscal_id"],
        codigo_item=row["codigo_item"],
        descricao=row["descricao"],
        quantidade=row["quantidade"],
        valor_unitario=row["valor_unitario"],
        valor_total_item=row["valor_total_item"],
    )


# --- Repositorio de notas -----------------------------------------------

def inserir_nota(nota: NotaFiscal, db_path: str = DEFAULT_DB_PATH) -> int:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """
            INSERT INTO nota_fiscal (
                chave_acesso, hash_conteudo, canal_origem, uf, cnpj_emitente,
                ano_mes_emissao, modelo, emitente_nome, data_emissao,
                valor_total, status, data_importacao
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                nota.chave_acesso,
                nota.hash_conteudo,
                nota.canal_origem.value,
                nota.uf,
                nota.cnpj_emitente,
                nota.ano_mes_emissao,
                nota.modelo,
                nota.emitente_nome,
                nota.data_emissao,
                nota.valor_total,
                nota.status.value,
                nota.data_importacao,
            ),
        )
        conn.commit()
        nota.id = cursor.lastrowid
        return nota.id
    finally:
        conn.close()


def inserir_itens(itens: list[ItemNota], db_path: str = DEFAULT_DB_PATH) -> None:
    if not itens:
        return
    conn = get_connection(db_path)
    try:
        conn.executemany(
            """
            INSERT INTO item_nota (
                nota_fiscal_id, codigo_item, descricao, quantidade,
                valor_unitario, valor_total_item
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item.nota_fiscal_id,
                    item.codigo_item,
                    item.descricao,
                    item.quantidade,
                    item.valor_unitario,
                    item.valor_total_item,
                )
                for item in itens
            ],
        )
        conn.commit()
    finally:
        conn.close()


def buscar_por_chave_acesso(chave_acesso: str, db_path: str = DEFAULT_DB_PATH) -> NotaFiscal | None:
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM nota_fiscal WHERE chave_acesso = ?", (chave_acesso,)
        ).fetchone()
        return _row_to_nota(row) if row else None
    finally:
        conn.close()


def buscar_por_hash_conteudo(hash_conteudo: str, db_path: str = DEFAULT_DB_PATH) -> NotaFiscal | None:
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM nota_fiscal WHERE hash_conteudo = ?", (hash_conteudo,)
        ).fetchone()
        return _row_to_nota(row) if row else None
    finally:
        conn.close()


def buscar_nota_por_id(nota_id: int, db_path: str = DEFAULT_DB_PATH) -> NotaFiscal | None:
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM nota_fiscal WHERE id = ?", (nota_id,)).fetchone()
        return _row_to_nota(row) if row else None
    finally:
        conn.close()


def listar_itens_por_nota(nota_fiscal_id: int, db_path: str = DEFAULT_DB_PATH) -> list[ItemNota]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM item_nota WHERE nota_fiscal_id = ?", (nota_fiscal_id,)
        ).fetchall()
        return [_row_to_item(row) for row in rows]
    finally:
        conn.close()


def listar_notas(mes: str | None = None, db_path: str = DEFAULT_DB_PATH) -> list[NotaFiscal]:
    """Lista notas ordenadas pela data de emissao (ou ano-mes, quando o dia
    exato nao foi obtido) desc. Filtro opcional por mes no formato AAAA-MM."""
    conn = get_connection(db_path)
    try:
        query = """
            SELECT *, COALESCE(substr(data_emissao, 1, 7), '20' || substr(ano_mes_emissao, 1, 2) || '-' || substr(ano_mes_emissao, 3, 2)) AS mes_ordenacao
            FROM nota_fiscal
        """
        params: tuple = ()
        if mes:
            query += " WHERE COALESCE(substr(data_emissao, 1, 7), '20' || substr(ano_mes_emissao, 1, 2) || '-' || substr(ano_mes_emissao, 3, 2)) = ?"
            params = (mes,)
        query += " ORDER BY mes_ordenacao DESC, id DESC"
        rows = conn.execute(query, params).fetchall()
        return [_row_to_nota(row) for row in rows]
    finally:
        conn.close()


# --- Repositorio da fila de processamento OCR ---------------------------

def inserir_envio(
    caminho_arquivo: str,
    tipo_arquivo: str,
    hash_conteudo: str,
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """
            INSERT INTO envio_ocr (caminho_arquivo, tipo_arquivo, hash_conteudo, status, data_envio)
            VALUES (?, ?, ?, 'pendente', ?)
            """,
            (caminho_arquivo, tipo_arquivo, hash_conteudo, datetime.now().isoformat()),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def atualizar_status_envio(
    envio_id: int,
    status: str,
    nota_fiscal_id: int | None = None,
    marcar_processado_agora: bool = False,
    db_path: str = DEFAULT_DB_PATH,
) -> None:
    conn = get_connection(db_path)
    try:
        data_processamento = datetime.now().isoformat() if marcar_processado_agora else None
        conn.execute(
            """
            UPDATE envio_ocr
            SET status = ?,
                nota_fiscal_id = COALESCE(?, nota_fiscal_id),
                data_processamento = COALESCE(?, data_processamento)
            WHERE id = ?
            """,
            (status, nota_fiscal_id, data_processamento, envio_id),
        )
        conn.commit()
    finally:
        conn.close()


def buscar_envio_por_id(envio_id: int, db_path: str = DEFAULT_DB_PATH) -> sqlite3.Row | None:
    conn = get_connection(db_path)
    try:
        return conn.execute("SELECT * FROM envio_ocr WHERE id = ?", (envio_id,)).fetchone()
    finally:
        conn.close()


def buscar_proximo_envio_pendente(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Row | None:
    """FIFO: o envio pendente mais antigo (por data_envio, depois id)."""
    conn = get_connection(db_path)
    try:
        return conn.execute(
            "SELECT * FROM envio_ocr WHERE status = 'pendente' ORDER BY data_envio ASC, id ASC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()


def reconciliar_processando_para_pendente(db_path: str = DEFAULT_DB_PATH) -> int:
    """Reverte envios presos em 'processando' (interrompidos por queda do
    processo) de volta para 'pendente', para que o worker os retome ao
    iniciar (research.md #11, Principio VII)."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute("UPDATE envio_ocr SET status = 'pendente' WHERE status = 'processando'")
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()
