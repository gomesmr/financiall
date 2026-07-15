from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path

from src.models.categoria import Categoria
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

CREATE TABLE IF NOT EXISTS categoria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    nome_normalizado TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_categoria_nome_normalizado
    ON categoria(nome_normalizado);
"""


def _garantir_coluna_categoria_id(conn: sqlite3.Connection) -> None:
    """Adiciona nota_fiscal.categoria_id via ALTER TABLE idempotente
    (research.md #1 da feature 003) -- 'CREATE TABLE IF NOT EXISTS' nao
    altera uma tabela ja existente, e o banco de producao/dev no
    Raspberry Pi ja tem dados reais sem essa coluna."""
    colunas = {row["name"] for row in conn.execute("PRAGMA table_info(nota_fiscal)").fetchall()}
    if "categoria_id" not in colunas:
        conn.execute("ALTER TABLE nota_fiscal ADD COLUMN categoria_id INTEGER REFERENCES categoria(id)")


def _garantir_coluna_titular(conn: sqlite3.Connection) -> None:
    """Adiciona nota_fiscal.titular via ALTER TABLE idempotente (mesmo
    padrao de categoria_id, research.md #1 da feature 004). Validacao de
    valor (marcelo/cristine/nao_identificado) fica na camada de servico,
    nao em CHECK do schema (research.md #1)."""
    colunas = {row["name"] for row in conn.execute("PRAGMA table_info(nota_fiscal)").fetchall()}
    if "titular" not in colunas:
        conn.execute("ALTER TABLE nota_fiscal ADD COLUMN titular TEXT")


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
        _garantir_coluna_categoria_id(conn)
        _garantir_coluna_titular(conn)
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
        categoria_id=row["categoria_id"],
        titular=row["titular"],
    )


def _row_to_categoria(row: sqlite3.Row) -> Categoria:
    return Categoria(id=row["id"], nome=row["nome"])


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


def inserir_nota_com_itens(nota: NotaFiscal, itens: list[ItemNota], db_path: str = DEFAULT_DB_PATH) -> int:
    """Grava a nota e seus itens numa unica transacao (research.md #6 da
    feature 004) -- diferente de inserir_nota/inserir_itens (duas
    conexoes/commits separados), necessario aqui porque uma interrupcao
    no meio de uma importacao em lote nao pode deixar nota sem itens."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """
            INSERT INTO nota_fiscal (
                chave_acesso, hash_conteudo, canal_origem, uf, cnpj_emitente,
                ano_mes_emissao, modelo, emitente_nome, data_emissao,
                valor_total, status, data_importacao, categoria_id, titular
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                nota.categoria_id,
                nota.titular,
            ),
        )
        nota_id = cursor.lastrowid

        if itens:
            conn.executemany(
                """
                INSERT INTO item_nota (
                    nota_fiscal_id, codigo_item, descricao, quantidade,
                    valor_unitario, valor_total_item
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (nota_id, item.codigo_item, item.descricao, item.quantidade, item.valor_unitario, item.valor_total_item)
                    for item in itens
                ],
            )

        conn.commit()
        nota.id = nota_id
        return nota_id
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


def listar_notas(
    mes: str | None = None, titular: str | None = None, db_path: str = DEFAULT_DB_PATH
) -> list[NotaFiscal]:
    """Lista notas ordenadas pela data de emissao (ou ano-mes, quando o dia
    exato nao foi obtido) desc. Filtros opcionais por mes (AAAA-MM) e por
    titular (feature 004)."""
    conn = get_connection(db_path)
    try:
        query = """
            SELECT *, COALESCE(substr(data_emissao, 1, 7), '20' || substr(ano_mes_emissao, 1, 2) || '-' || substr(ano_mes_emissao, 3, 2)) AS mes_ordenacao
            FROM nota_fiscal
        """
        condicoes: list[str] = []
        params: list = []
        if mes:
            condicoes.append(
                "COALESCE(substr(data_emissao, 1, 7), '20' || substr(ano_mes_emissao, 1, 2) || '-' || substr(ano_mes_emissao, 3, 2)) = ?"
            )
            params.append(mes)
        if titular:
            condicoes.append("titular = ?")
            params.append(titular)
        if condicoes:
            query += " WHERE " + " AND ".join(condicoes)
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


# --- Exclusao de nota (feature 002) -------------------------------------

def excluir_nota(nota_id: int, db_path: str = DEFAULT_DB_PATH) -> list[str] | None:
    """Exclui a nota, seus itens e os envios que a originaram numa unica
    transacao (data-model.md - Operacao excluir_nota). Retorna a lista de
    `caminho_arquivo` dos envios excluidos (para o chamador remover os
    arquivos do disco - research.md #2), ou None se a nota nao existia."""
    conn = get_connection(db_path)
    try:
        existe = conn.execute(
            "SELECT 1 FROM nota_fiscal WHERE id = ?", (nota_id,)
        ).fetchone()
        if existe is None:
            return None

        caminhos = [
            row["caminho_arquivo"]
            for row in conn.execute(
                "SELECT caminho_arquivo FROM envio_ocr WHERE nota_fiscal_id = ?", (nota_id,)
            ).fetchall()
        ]
        conn.execute("DELETE FROM envio_ocr WHERE nota_fiscal_id = ?", (nota_id,))
        conn.execute("DELETE FROM item_nota WHERE nota_fiscal_id = ?", (nota_id,))
        conn.execute("DELETE FROM nota_fiscal WHERE id = ?", (nota_id,))
        conn.commit()
        return caminhos
    finally:
        conn.close()


# --- Repositorio de categorias (feature 003) -----------------------------

def _normalizar_nome(nome: str) -> str:
    return nome.strip().casefold()


def criar_categoria(nome: str, db_path: str = DEFAULT_DB_PATH) -> int | None:
    """Cria uma categoria. Retorna o id novo, ou None se o nome (apos
    strip()) for vazio ou ja existir (indice unico violado, research.md
    #2 -- casefold() cobre acentuacao em portugues, ao contrario de
    COLLATE NOCASE)."""
    nome_limpo = nome.strip()
    nome_normalizado = _normalizar_nome(nome)
    if not nome_limpo:
        return None
    conn = get_connection(db_path)
    try:
        try:
            cursor = conn.execute(
                "INSERT INTO categoria (nome, nome_normalizado) VALUES (?, ?)",
                (nome_limpo, nome_normalizado),
            )
        except sqlite3.IntegrityError:
            return None
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def listar_categorias(db_path: str = DEFAULT_DB_PATH) -> list[Categoria]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute("SELECT * FROM categoria ORDER BY nome").fetchall()
        return [_row_to_categoria(row) for row in rows]
    finally:
        conn.close()


def buscar_categoria_por_id(categoria_id: int, db_path: str = DEFAULT_DB_PATH) -> Categoria | None:
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM categoria WHERE id = ?", (categoria_id,)).fetchone()
        return _row_to_categoria(row) if row else None
    finally:
        conn.close()


def editar_categoria(categoria_id: int, novo_nome: str, db_path: str = DEFAULT_DB_PATH) -> bool | None:
    """Renomeia uma categoria existente, mesma validacao de unicidade de
    criar_categoria. Retorna None se a categoria nao existe, False se o
    novo nome e invalido/duplicado, True em sucesso."""
    conn = get_connection(db_path)
    try:
        existe = conn.execute("SELECT 1 FROM categoria WHERE id = ?", (categoria_id,)).fetchone()
        if existe is None:
            return None

        nome_limpo = novo_nome.strip()
        if not nome_limpo:
            return False

        try:
            conn.execute(
                "UPDATE categoria SET nome = ?, nome_normalizado = ? WHERE id = ?",
                (nome_limpo, _normalizar_nome(novo_nome), categoria_id),
            )
        except sqlite3.IntegrityError:
            return False
        conn.commit()
        return True
    finally:
        conn.close()


def excluir_categoria(categoria_id: int, db_path: str = DEFAULT_DB_PATH) -> bool:
    """Exclui a categoria; notas que a usavam voltam a 'sem categoria'
    (research.md #3 -- transacao unica, sem depender de ON DELETE
    declarado na FK). Retorna False se a categoria nao existia."""
    conn = get_connection(db_path)
    try:
        existe = conn.execute("SELECT 1 FROM categoria WHERE id = ?", (categoria_id,)).fetchone()
        if existe is None:
            return False

        conn.execute("UPDATE nota_fiscal SET categoria_id = NULL WHERE categoria_id = ?", (categoria_id,))
        conn.execute("DELETE FROM categoria WHERE id = ?", (categoria_id,))
        conn.commit()
        return True
    finally:
        conn.close()


def atribuir_categoria_a_nota(
    nota_id: int, categoria_id: int | None, db_path: str = DEFAULT_DB_PATH
) -> bool | None:
    """Atribui, troca ou remove (categoria_id=None) a categoria de uma
    nota. Retorna None se a nota nao existe; False se categoria_id foi
    informado mas nao existe como categoria; True em sucesso."""
    conn = get_connection(db_path)
    try:
        nota_existe = conn.execute("SELECT 1 FROM nota_fiscal WHERE id = ?", (nota_id,)).fetchone()
        if nota_existe is None:
            return None

        if categoria_id is not None:
            categoria_existe = conn.execute(
                "SELECT 1 FROM categoria WHERE id = ?", (categoria_id,)
            ).fetchone()
            if categoria_existe is None:
                return False

        conn.execute("UPDATE nota_fiscal SET categoria_id = ? WHERE id = ?", (categoria_id, nota_id))
        conn.commit()
        return True
    finally:
        conn.close()
