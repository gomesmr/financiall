from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path

from src.models.categoria import Categoria
from src.models.item_nota import ItemNota
from src.models.nota_fiscal import TITULARES_VALIDOS, CanalOrigem, NotaFiscal, StatusNota

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

CREATE TABLE IF NOT EXISTS cache_descricao_categoria (
    descricao_normalizada TEXT PRIMARY KEY,
    categoria_id INTEGER NOT NULL REFERENCES categoria(id)
);

CREATE TABLE IF NOT EXISTS regra_categoria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    padrao TEXT NOT NULL,
    categoria_id INTEGER NOT NULL REFERENCES categoria(id),
    prioridade INTEGER NOT NULL DEFAULT 0,
    ativa INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS historico_classificacao_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_nota_id INTEGER NOT NULL REFERENCES item_nota(id),
    categoria_id_anterior INTEGER,
    categoria_id_nova INTEGER,
    metodo TEXT NOT NULL,
    timestamp TEXT NOT NULL
);
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


def _garantir_coluna_titular_envio(conn: sqlite3.Connection) -> None:
    """Adiciona envio_ocr.titular via ALTER TABLE idempotente (mesmo
    padrao de nota_fiscal.titular) -- o titular escolhido pelo usuario no
    momento do envio de foto/PDF precisa sobreviver ate o worker
    processar o envio de forma assincrona (feature: escolher titular na
    importacao)."""
    colunas = {row["name"] for row in conn.execute("PRAGMA table_info(envio_ocr)").fetchall()}
    if "titular" not in colunas:
        conn.execute("ALTER TABLE envio_ocr ADD COLUMN titular TEXT")


def _garantir_coluna_parent_id_categoria(conn: sqlite3.Connection) -> None:
    """Adiciona categoria.parent_id via ALTER TABLE idempotente
    (data-model.md da feature 008) -- categorias ja existentes (todas sem
    hierarquia) viram automaticamente categorias de topo, sem migracao de
    dado necessaria (research.md #3)."""
    colunas = {row["name"] for row in conn.execute("PRAGMA table_info(categoria)").fetchall()}
    if "parent_id" not in colunas:
        conn.execute("ALTER TABLE categoria ADD COLUMN parent_id INTEGER REFERENCES categoria(id)")


def _garantir_indices_categoria_por_nivel(conn: sqlite3.Connection) -> None:
    """Substitui o indice unico global de categoria.nome_normalizado
    (feature 003) por dois indices parciais escopados por nivel --
    research.md #19, data-model.md. Seguro para o dado de producao
    existente: toda categoria hoje e de topo, entao a troca e
    comportamentalmente equivalente ate a primeira subcategoria ser
    criada."""
    conn.execute("DROP INDEX IF EXISTS idx_categoria_nome_normalizado")
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_categoria_topo_nome_normalizado
            ON categoria(nome_normalizado) WHERE parent_id IS NULL
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_categoria_subcategoria_nome_normalizado
            ON categoria(parent_id, nome_normalizado) WHERE parent_id IS NOT NULL
        """
    )


def _garantir_colunas_classificacao_item(conn: sqlite3.Connection) -> None:
    """Adiciona item_nota.categoria_id/descricao_normalizada/
    metodo_classificacao via ALTER TABLE idempotente (data-model.md da
    feature 008) -- itens ja existentes ficam automaticamente pendentes
    (categoria_id NULL), sem migracao de dado necessaria (research.md #9)."""
    colunas = {row["name"] for row in conn.execute("PRAGMA table_info(item_nota)").fetchall()}
    if "categoria_id" not in colunas:
        conn.execute("ALTER TABLE item_nota ADD COLUMN categoria_id INTEGER REFERENCES categoria(id)")
    if "descricao_normalizada" not in colunas:
        conn.execute("ALTER TABLE item_nota ADD COLUMN descricao_normalizada TEXT")
    if "metodo_classificacao" not in colunas:
        conn.execute(
            "ALTER TABLE item_nota ADD COLUMN metodo_classificacao TEXT "
            "CHECK (metodo_classificacao IN ('cache', 'regra', 'manual'))"
        )


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
        _garantir_coluna_titular_envio(conn)
        _garantir_coluna_parent_id_categoria(conn)
        _garantir_indices_categoria_por_nivel(conn)
        _garantir_colunas_classificacao_item(conn)
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
    return Categoria(id=row["id"], nome=row["nome"], parent_id=row["parent_id"])


def _row_to_item(row: sqlite3.Row) -> ItemNota:
    return ItemNota(
        id=row["id"],
        nota_fiscal_id=row["nota_fiscal_id"],
        codigo_item=row["codigo_item"],
        descricao=row["descricao"],
        quantidade=row["quantidade"],
        valor_unitario=row["valor_unitario"],
        valor_total_item=row["valor_total_item"],
        categoria_id=row["categoria_id"],
        descricao_normalizada=row["descricao_normalizada"],
        metodo_classificacao=row["metodo_classificacao"],
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
    mes: str | None = None,
    titular: str | None = None,
    categoria_id: int | None = None,
    db_path: str = DEFAULT_DB_PATH,
) -> list[NotaFiscal]:
    """Lista notas ordenadas pela data de emissao (ou ano-mes, quando o dia
    exato nao foi obtido) desc. Filtros opcionais por mes (AAAA-MM), por
    titular (feature 004) e por categoria_id -- tipo de estabelecimento da
    nota (feature 009)."""
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
        if categoria_id is not None:
            condicoes.append("categoria_id = ?")
            params.append(categoria_id)
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
    titular: str | None = None,
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """
            INSERT INTO envio_ocr (caminho_arquivo, tipo_arquivo, hash_conteudo, status, data_envio, titular)
            VALUES (?, ?, ?, 'pendente', ?, ?)
            """,
            (caminho_arquivo, tipo_arquivo, hash_conteudo, datetime.now().isoformat(), titular),
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


def criar_categoria(nome: str, parent_id: int | None = None, db_path: str = DEFAULT_DB_PATH) -> int | None:
    """Cria uma categoria (parent_id=None) ou subcategoria (parent_id
    preenchido). Retorna o id novo, ou None se: o nome (apos strip()) for
    vazio; ja existir no mesmo nivel (indice unico parcial escopado por
    nivel, research.md #19 -- casefold() cobre acentuacao em portugues,
    ao contrario de COLLATE NOCASE); parent_id informado nao existir; ou
    parent_id apontar para uma categoria que ja e, ela propria, uma
    subcategoria (2 niveis fixos, research.md #3)."""
    nome_limpo = nome.strip()
    nome_normalizado = _normalizar_nome(nome)
    if not nome_limpo:
        return None
    conn = get_connection(db_path)
    try:
        if parent_id is not None:
            linha_pai = conn.execute(
                "SELECT parent_id FROM categoria WHERE id = ?", (parent_id,)
            ).fetchone()
            if linha_pai is None or linha_pai["parent_id"] is not None:
                return None

        try:
            cursor = conn.execute(
                "INSERT INTO categoria (nome, nome_normalizado, parent_id) VALUES (?, ?, ?)",
                (nome_limpo, nome_normalizado, parent_id),
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


def atribuir_titular_a_nota(
    nota_id: int, titular: str | None, db_path: str = DEFAULT_DB_PATH
) -> bool | None:
    """Atribui, troca ou remove (titular=None) o titular de uma nota.
    Retorna None se a nota nao existe; False se titular foi informado mas
    nao e um dos valores conhecidos (TITULARES_VALIDOS); True em
    sucesso. Mesmo padrao de `atribuir_categoria_a_nota`."""
    if titular is not None and titular not in TITULARES_VALIDOS:
        return False

    conn = get_connection(db_path)
    try:
        nota_existe = conn.execute("SELECT 1 FROM nota_fiscal WHERE id = ?", (nota_id,)).fetchone()
        if nota_existe is None:
            return None

        conn.execute("UPDATE nota_fiscal SET titular = ? WHERE id = ?", (titular, nota_id))
        conn.commit()
        return True
    finally:
        conn.close()


# --- Repositorio de classificacao de itens (feature 008) -----------------

def classificar_item_automaticamente(
    item_id: int,
    categoria_id: int,
    metodo: str,
    descricao_normalizada: str,
    db_path: str = DEFAULT_DB_PATH,
) -> None:
    """Usada pela cascata (research.md #8, data-model.md). So roda sobre
    itens pendentes, entao categoria_id_anterior e sempre NULL no
    historico. Uma transacao: grava item_nota (categoria, metodo e a
    descricao normalizada calculada no momento da classificacao --
    research.md #2), upsert em cache_descricao_categoria (research.md
    #10) e INSERT em historico_classificacao_item (FR-014)."""
    conn = get_connection(db_path)
    try:
        conn.execute(
            "UPDATE item_nota SET categoria_id = ?, metodo_classificacao = ?, descricao_normalizada = ? WHERE id = ?",
            (categoria_id, metodo, descricao_normalizada, item_id),
        )
        conn.execute(
            """
            INSERT INTO cache_descricao_categoria (descricao_normalizada, categoria_id)
            VALUES (?, ?)
            ON CONFLICT(descricao_normalizada) DO UPDATE SET categoria_id = excluded.categoria_id
            """,
            (descricao_normalizada, categoria_id),
        )
        conn.execute(
            """
            INSERT INTO historico_classificacao_item
                (item_nota_id, categoria_id_anterior, categoria_id_nova, metodo, timestamp)
            VALUES (?, NULL, ?, ?, ?)
            """,
            (item_id, categoria_id, metodo, datetime.now().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def definir_descricao_normalizada_item(item_id: int, descricao_normalizada: str, db_path: str = DEFAULT_DB_PATH) -> None:
    """Persiste so a descricao normalizada de um item que permaneceu
    pendente (Tier 3, sem categoria) -- necessario para a fila de
    pendentes poder agrupar por descricao_normalizada (T013) mesmo antes
    de qualquer classificacao acontecer."""
    conn = get_connection(db_path)
    try:
        conn.execute(
            "UPDATE item_nota SET descricao_normalizada = ? WHERE id = ?",
            (descricao_normalizada, item_id),
        )
        conn.commit()
    finally:
        conn.close()


def listar_itens_pendentes(nota_fiscal_id: int | None = None, db_path: str = DEFAULT_DB_PATH) -> dict:
    """Fila de revisao (FR-009, data-model.md). Sem `nota_fiscal_id`:
    agrupado por `descricao_normalizada` (itens sem descricao nunca
    normalizada ficam de fora do agrupamento -- nao ha base para agrupar
    "nenhuma descricao" -- mas continuam visiveis na visao por nota
    abaixo), com a contagem agregada pendente vs. total (research.md
    #21, SC-002). Com `nota_fiscal_id`: todos os itens pendentes daquela
    nota, sem agrupamento -- a visao "por nota" do FR-009."""
    conn = get_connection(db_path)
    try:
        if nota_fiscal_id is not None:
            itens = conn.execute(
                """
                SELECT id, descricao, quantidade, valor_total_item
                FROM item_nota
                WHERE nota_fiscal_id = ? AND categoria_id IS NULL
                """,
                (nota_fiscal_id,),
            ).fetchall()
            return {
                "itens": [
                    {
                        "id": row["id"],
                        "descricao": row["descricao"],
                        "quantidade": row["quantidade"],
                        "valor_total_item": row["valor_total_item"],
                    }
                    for row in itens
                ]
            }

        grupos = conn.execute(
            """
            SELECT descricao_normalizada, COUNT(*) AS quantidade_itens, MIN(id) AS exemplo_item_id
            FROM item_nota
            WHERE categoria_id IS NULL AND descricao_normalizada IS NOT NULL
            GROUP BY descricao_normalizada
            ORDER BY quantidade_itens DESC
            """
        ).fetchall()
        total_pendente = conn.execute("SELECT COUNT(*) FROM item_nota WHERE categoria_id IS NULL").fetchone()[0]
        total_itens = conn.execute("SELECT COUNT(*) FROM item_nota").fetchone()[0]
        return {
            "resumo": {"total_pendente": total_pendente, "total_itens": total_itens},
            "grupos": [
                {
                    "descricao_normalizada": row["descricao_normalizada"],
                    "quantidade_itens": row["quantidade_itens"],
                    "exemplo_item_id": row["exemplo_item_id"],
                }
                for row in grupos
            ],
        }
    finally:
        conn.close()


def _classificar_item_manual_tx(
    conn: sqlite3.Connection,
    item_id: int,
    categoria_id: int,
    categoria_id_anterior: int | None,
    descricao_normalizada: str | None,
) -> None:
    """Parte comum de `atribuir_categoria_manual`/`classificar_grupo_pendente`
    -- grava um item dentro de uma transacao ja aberta pelo chamador, sem
    fazer commit/close (permite que a resolucao em grupo aconteca numa
    unica transacao)."""
    conn.execute(
        "UPDATE item_nota SET categoria_id = ?, metodo_classificacao = 'manual' WHERE id = ?",
        (categoria_id, item_id),
    )
    if descricao_normalizada:
        conn.execute(
            """
            INSERT INTO cache_descricao_categoria (descricao_normalizada, categoria_id)
            VALUES (?, ?)
            ON CONFLICT(descricao_normalizada) DO UPDATE SET categoria_id = excluded.categoria_id
            """,
            (descricao_normalizada, categoria_id),
        )
    conn.execute(
        """
        INSERT INTO historico_classificacao_item
            (item_nota_id, categoria_id_anterior, categoria_id_nova, metodo, timestamp)
        VALUES (?, ?, ?, 'manual', ?)
        """,
        (item_id, categoria_id_anterior, categoria_id, datetime.now().isoformat()),
    )


def atribuir_categoria_manual(item_id: int, categoria_id: int, db_path: str = DEFAULT_DB_PATH) -> bool | None:
    """Usada pela fila de pendentes (US1) e pela correcao simples (US4
    cenario 1). Retorna None se o item nao existe; False se categoria_id
    informado nao existe; True em sucesso. Em sucesso, quando o item de
    origem estava pendente (`categoria_id_anterior IS NULL`), resolve
    tambem -- na mesma transacao -- todos os demais `item_nota` pendentes
    com a mesma `descricao_normalizada` (research.md #15, cada um com sua
    propria linha de historico); corrigir um item ja classificado (US4)
    nunca dispara esse efeito colateral."""
    conn = get_connection(db_path)
    try:
        item = conn.execute(
            "SELECT categoria_id, descricao_normalizada FROM item_nota WHERE id = ?", (item_id,)
        ).fetchone()
        if item is None:
            return None

        categoria_existe = conn.execute("SELECT 1 FROM categoria WHERE id = ?", (categoria_id,)).fetchone()
        if categoria_existe is None:
            return False

        categoria_anterior = item["categoria_id"]
        descricao_normalizada = item["descricao_normalizada"]
        estava_pendente = categoria_anterior is None

        _classificar_item_manual_tx(conn, item_id, categoria_id, categoria_anterior, descricao_normalizada)

        if estava_pendente and descricao_normalizada:
            outros_ids = [
                row["id"]
                for row in conn.execute(
                    "SELECT id FROM item_nota WHERE descricao_normalizada = ? AND categoria_id IS NULL AND id != ?",
                    (descricao_normalizada, item_id),
                ).fetchall()
            ]
            for outro_id in outros_ids:
                _classificar_item_manual_tx(conn, outro_id, categoria_id, None, descricao_normalizada)

        conn.commit()
        return True
    finally:
        conn.close()


def classificar_grupo_pendente(
    descricao_normalizada: str, categoria_id: int, db_path: str = DEFAULT_DB_PATH
) -> int | None:
    """Mesma operacao de `atribuir_categoria_manual` (reaproveitada
    internamente -- research.md #15, sem duplicar a logica de resolucao
    em grupo), so que entrando pela descricao normalizada em vez de por
    um item especifico (conveniencia da fila agrupada, US1 cenario 1).
    Retorna None se categoria_id nao existe; a quantidade de itens
    afetados (>= 0) em sucesso."""
    conn = get_connection(db_path)
    try:
        categoria_existe = conn.execute("SELECT 1 FROM categoria WHERE id = ?", (categoria_id,)).fetchone()
        if categoria_existe is None:
            return None

        itens_ids = [
            row["id"]
            for row in conn.execute(
                "SELECT id FROM item_nota WHERE descricao_normalizada = ? AND categoria_id IS NULL",
                (descricao_normalizada,),
            ).fetchall()
        ]
    finally:
        conn.close()

    if not itens_ids:
        return 0

    atribuir_categoria_manual(itens_ids[0], categoria_id, db_path=db_path)
    return len(itens_ids)


def calcular_impacto_correcao_fonte(item_id: int, db_path: str = DEFAULT_DB_PATH) -> dict | None:
    """Previa de 'corrigir a fonte e reclassificar o passado' (FR-013,
    SC-006, data-model.md). Retorna None se o item nao existe; senao a
    contagem de item_nota com a mesma descricao_normalizada E a mesma
    categoria_id atual do item -- o raio de efeito real da correcao
    abaixo, antes de aplicar."""
    conn = get_connection(db_path)
    try:
        item = conn.execute(
            "SELECT descricao_normalizada, categoria_id FROM item_nota WHERE id = ?", (item_id,)
        ).fetchone()
        if item is None:
            return None

        quantidade = conn.execute(
            "SELECT COUNT(*) FROM item_nota WHERE descricao_normalizada = ? AND categoria_id = ?",
            (item["descricao_normalizada"], item["categoria_id"]),
        ).fetchone()[0]

        return {
            "descricao_normalizada": item["descricao_normalizada"],
            "categoria_id_atual": item["categoria_id"],
            "quantidade_itens_afetados": quantidade,
        }
    finally:
        conn.close()


def corrigir_fonte_e_reclassificar(
    item_id: int, nova_categoria_id: int, db_path: str = DEFAULT_DB_PATH
) -> int | None:
    """Aplica a correcao de research.md #11: upsert do cache para a
    descricao_normalizada do item corrigido, `UPDATE` em lote de todos os
    `item_nota` com a mesma descricao_normalizada e a mesma categoria
    antiga (incorreta) para a nova, e uma linha de historico por item
    afetado. Retorna a quantidade de itens atualizados, ou None se o
    item de origem nao existe."""
    conn = get_connection(db_path)
    try:
        item = conn.execute(
            "SELECT descricao_normalizada, categoria_id FROM item_nota WHERE id = ?", (item_id,)
        ).fetchone()
        if item is None:
            return None

        descricao_normalizada = item["descricao_normalizada"]
        categoria_anterior = item["categoria_id"]

        if descricao_normalizada:
            conn.execute(
                """
                INSERT INTO cache_descricao_categoria (descricao_normalizada, categoria_id)
                VALUES (?, ?)
                ON CONFLICT(descricao_normalizada) DO UPDATE SET categoria_id = excluded.categoria_id
                """,
                (descricao_normalizada, nova_categoria_id),
            )

        itens_afetados_ids = [
            row["id"]
            for row in conn.execute(
                "SELECT id FROM item_nota WHERE descricao_normalizada = ? AND categoria_id = ?",
                (descricao_normalizada, categoria_anterior),
            ).fetchall()
        ]

        for afetado_id in itens_afetados_ids:
            conn.execute(
                "UPDATE item_nota SET categoria_id = ?, metodo_classificacao = 'manual' WHERE id = ?",
                (nova_categoria_id, afetado_id),
            )
            conn.execute(
                """
                INSERT INTO historico_classificacao_item
                    (item_nota_id, categoria_id_anterior, categoria_id_nova, metodo, timestamp)
                VALUES (?, ?, ?, 'manual', ?)
                """,
                (afetado_id, categoria_anterior, nova_categoria_id, datetime.now().isoformat()),
            )

        conn.commit()
        return len(itens_afetados_ids)
    finally:
        conn.close()


def calcular_impacto_exclusao(categoria_id: int, db_path: str = DEFAULT_DB_PATH) -> dict | None:
    """Previa de exclusao (FR-004, FR-017, data-model.md). Retorna None se
    a categoria nao existe; senao {"tem_subcategorias", "quantidade_itens",
    "quantidade_cache", "quantidade_regras"}. tem_subcategorias=True MUST
    bloquear a exclusao antes de qualquer outro calculo (FR-017) --
    calculado aqui mesmo assim, para o cliente montar a previa completa."""
    conn = get_connection(db_path)
    try:
        existe = conn.execute("SELECT 1 FROM categoria WHERE id = ?", (categoria_id,)).fetchone()
        if existe is None:
            return None

        tem_subcategorias = (
            conn.execute("SELECT 1 FROM categoria WHERE parent_id = ?", (categoria_id,)).fetchone()
            is not None
        )
        quantidade_itens = conn.execute(
            "SELECT COUNT(*) FROM item_nota WHERE categoria_id = ?", (categoria_id,)
        ).fetchone()[0]
        quantidade_cache = conn.execute(
            "SELECT COUNT(*) FROM cache_descricao_categoria WHERE categoria_id = ?", (categoria_id,)
        ).fetchone()[0]
        quantidade_regras = conn.execute(
            "SELECT COUNT(*) FROM regra_categoria WHERE categoria_id = ?", (categoria_id,)
        ).fetchone()[0]

        return {
            "tem_subcategorias": tem_subcategorias,
            "quantidade_itens": quantidade_itens,
            "quantidade_cache": quantidade_cache,
            "quantidade_regras": quantidade_regras,
        }
    finally:
        conn.close()


def excluir_categoria_com_destino(
    categoria_id: int,
    destino: str,
    categoria_substituta_id: int | None = None,
    db_path: str = DEFAULT_DB_PATH,
) -> bool | None:
    """Exclusao com destino explicito (research.md #12, data-model.md).
    `destino` e "substituta" ou "pendente". Retorna None se a categoria
    nao existe; False se tem subcategorias (bloqueado, FR-017), se
    `destino` for invalido, ou se `categoria_substituta_id` for
    invalido/de nivel diferente da categoria excluida; True em sucesso.
    Nota fiscal que usava a categoria (feature 003) sempre volta a 'sem
    categoria', independente do destino escolhido para item/cache/regra."""
    conn = get_connection(db_path)
    try:
        categoria = conn.execute("SELECT parent_id FROM categoria WHERE id = ?", (categoria_id,)).fetchone()
        if categoria is None:
            return None

        tem_subcategorias = (
            conn.execute("SELECT 1 FROM categoria WHERE parent_id = ?", (categoria_id,)).fetchone()
            is not None
        )
        if tem_subcategorias:
            return False

        if destino == "substituta":
            if categoria_substituta_id is None:
                return False
            substituta = conn.execute(
                "SELECT parent_id FROM categoria WHERE id = ?", (categoria_substituta_id,)
            ).fetchone()
            if substituta is None:
                return False
            if (categoria["parent_id"] is None) != (substituta["parent_id"] is None):
                return False

            conn.execute(
                "UPDATE item_nota SET categoria_id = ? WHERE categoria_id = ?",
                (categoria_substituta_id, categoria_id),
            )
            conn.execute(
                "UPDATE cache_descricao_categoria SET categoria_id = ? WHERE categoria_id = ?",
                (categoria_substituta_id, categoria_id),
            )
            conn.execute(
                "UPDATE regra_categoria SET categoria_id = ? WHERE categoria_id = ?",
                (categoria_substituta_id, categoria_id),
            )
        elif destino == "pendente":
            conn.execute(
                "UPDATE item_nota SET categoria_id = NULL, metodo_classificacao = NULL WHERE categoria_id = ?",
                (categoria_id,),
            )
            conn.execute("DELETE FROM cache_descricao_categoria WHERE categoria_id = ?", (categoria_id,))
            conn.execute("DELETE FROM regra_categoria WHERE categoria_id = ?", (categoria_id,))
        else:
            return False

        conn.execute("UPDATE nota_fiscal SET categoria_id = NULL WHERE categoria_id = ?", (categoria_id,))
        conn.execute("DELETE FROM categoria WHERE id = ?", (categoria_id,))
        conn.commit()
        return True
    finally:
        conn.close()
