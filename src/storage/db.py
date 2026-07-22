from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path

from src.models.categoria import Categoria
from src.models.estabelecimento import Estabelecimento
from src.models.item_nota import ItemNota
from src.models.nota_fiscal import TITULARES_VALIDOS, CanalOrigem, NotaFiscal, StatusNota
from src.models.transacao import NATUREZAS_VALIDAS, NaturezaTransacao, Transacao, TipoTransacao

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

CREATE TABLE IF NOT EXISTS estabelecimento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    documento TEXT,
    descricao_normalizada TEXT,
    nome_fantasia TEXT,
    tipo_categoria_id INTEGER REFERENCES categoria(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_estabelecimento_documento
    ON estabelecimento(documento) WHERE documento IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_estabelecimento_descricao
    ON estabelecimento(descricao_normalizada) WHERE documento IS NULL AND descricao_normalizada IS NOT NULL;

CREATE TABLE IF NOT EXISTS transacao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint TEXT NOT NULL,
    data TEXT NOT NULL,
    descricao TEXT NOT NULL,
    descricao_normalizada TEXT,
    valor INTEGER NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('entrada', 'saida')),
    natureza TEXT CHECK (natureza IN ('gasto', 'renda', 'transferencia_interna', 'pagamento_fatura', 'estorno_credito')),
    metodo_classificacao_natureza TEXT CHECK (metodo_classificacao_natureza IN ('cache', 'regra', 'manual', 'heuristica_conta')),
    categoria_id INTEGER REFERENCES categoria(id),
    conta TEXT NOT NULL,
    titular TEXT,
    fonte TEXT,
    nota_fiscal_id INTEGER REFERENCES nota_fiscal(id),
    estabelecimento_id INTEGER REFERENCES estabelecimento(id),
    data_importacao TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_transacao_fingerprint ON transacao(fingerprint);

CREATE UNIQUE INDEX IF NOT EXISTS idx_transacao_nota_fiscal
    ON transacao(nota_fiscal_id) WHERE nota_fiscal_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS cache_descricao_natureza (
    descricao_normalizada TEXT PRIMARY KEY,
    natureza TEXT NOT NULL,
    categoria_id INTEGER REFERENCES categoria(id)
);

CREATE TABLE IF NOT EXISTS regra_natureza (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    padrao TEXT NOT NULL,
    natureza TEXT NOT NULL,
    categoria_id INTEGER REFERENCES categoria(id),
    prioridade INTEGER NOT NULL DEFAULT 0,
    ativa INTEGER NOT NULL DEFAULT 1
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


def _row_to_transacao(row: sqlite3.Row) -> Transacao:
    return Transacao(
        id=row["id"],
        fingerprint=row["fingerprint"],
        data=row["data"],
        descricao=row["descricao"],
        descricao_normalizada=row["descricao_normalizada"],
        valor=row["valor"],
        tipo=TipoTransacao(row["tipo"]),
        natureza=row["natureza"],
        metodo_classificacao_natureza=row["metodo_classificacao_natureza"],
        categoria_id=row["categoria_id"],
        conta=row["conta"],
        titular=row["titular"],
        fonte=row["fonte"],
        nota_fiscal_id=row["nota_fiscal_id"],
        estabelecimento_id=row["estabelecimento_id"],
        data_importacao=row["data_importacao"],
    )


def _row_to_estabelecimento(row: sqlite3.Row) -> Estabelecimento:
    return Estabelecimento(
        id=row["id"],
        documento=row["documento"],
        descricao_normalizada=row["descricao_normalizada"],
        nome_fantasia=row["nome_fantasia"],
        tipo_categoria_id=row["tipo_categoria_id"],
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


def listar_itens_por_categoria(categoria_id: int, db_path: str = DEFAULT_DB_PATH) -> list[dict]:
    """Itens classificados numa categoria, com o contexto da nota (data,
    emitente) para exibicao -- usado para inspecionar o uso de uma
    categoria antes de exclui-la (pedido do usuario apos o bug de
    exclusao da feature 010)."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT it.id, it.descricao, it.quantidade, it.valor_total_item, it.nota_fiscal_id,
                   nf.data_emissao, nf.emitente_nome
            FROM item_nota it
            JOIN nota_fiscal nf ON nf.id = it.nota_fiscal_id
            WHERE it.categoria_id = ?
            ORDER BY nf.data_emissao DESC, it.id DESC
            """,
            (categoria_id,),
        ).fetchall()
        return [dict(row) for row in rows]
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
    "quantidade_cache", "quantidade_regras", "quantidade_transacoes",
    "quantidade_estabelecimentos", "quantidade_cache_natureza",
    "quantidade_regras_natureza"}. tem_subcategorias=True MUST bloquear a
    exclusao antes de qualquer outro calculo (FR-017) -- calculado aqui
    mesmo assim, para o cliente montar a previa completa. Os quatro
    ultimos campos existem porque a feature 010 passou a referenciar
    categoria a partir de transacao/estabelecimento tambem, alem de
    item/nota (research.md #4/#9)."""
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
        quantidade_transacoes = conn.execute(
            "SELECT COUNT(*) FROM transacao WHERE categoria_id = ?", (categoria_id,)
        ).fetchone()[0]
        quantidade_estabelecimentos = conn.execute(
            "SELECT COUNT(*) FROM estabelecimento WHERE tipo_categoria_id = ?", (categoria_id,)
        ).fetchone()[0]
        quantidade_cache_natureza = conn.execute(
            "SELECT COUNT(*) FROM cache_descricao_natureza WHERE categoria_id = ?", (categoria_id,)
        ).fetchone()[0]
        quantidade_regras_natureza = conn.execute(
            "SELECT COUNT(*) FROM regra_natureza WHERE categoria_id = ?", (categoria_id,)
        ).fetchone()[0]

        return {
            "tem_subcategorias": tem_subcategorias,
            "quantidade_itens": quantidade_itens,
            "quantidade_cache": quantidade_cache,
            "quantidade_regras": quantidade_regras,
            "quantidade_transacoes": quantidade_transacoes,
            "quantidade_estabelecimentos": quantidade_estabelecimentos,
            "quantidade_cache_natureza": quantidade_cache_natureza,
            "quantidade_regras_natureza": quantidade_regras_natureza,
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
    categoria', independente do destino escolhido para item/cache/regra.
    Transacao e estabelecimento (feature 010) seguem a mesma regra de
    nota_fiscal -- sao dado real, nunca sao apagados, so perdem a
    referencia ou ganham a substituta; cache/regra de natureza seguem a
    mesma regra de cache/regra de categoria de item (apagados no destino
    'pendente', ja que uma regra sem categoria de gasto associada perde o
    sentido quando natureza=gasto)."""
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
            conn.execute(
                "UPDATE transacao SET categoria_id = ? WHERE categoria_id = ?",
                (categoria_substituta_id, categoria_id),
            )
            conn.execute(
                "UPDATE estabelecimento SET tipo_categoria_id = ? WHERE tipo_categoria_id = ?",
                (categoria_substituta_id, categoria_id),
            )
            conn.execute(
                "UPDATE cache_descricao_natureza SET categoria_id = ? WHERE categoria_id = ?",
                (categoria_substituta_id, categoria_id),
            )
            conn.execute(
                "UPDATE regra_natureza SET categoria_id = ? WHERE categoria_id = ?",
                (categoria_substituta_id, categoria_id),
            )
        elif destino == "pendente":
            conn.execute(
                "UPDATE item_nota SET categoria_id = NULL, metodo_classificacao = NULL WHERE categoria_id = ?",
                (categoria_id,),
            )
            conn.execute("DELETE FROM cache_descricao_categoria WHERE categoria_id = ?", (categoria_id,))
            conn.execute("DELETE FROM regra_categoria WHERE categoria_id = ?", (categoria_id,))
            conn.execute(
                # so a categoria some -- metodo_classificacao_natureza descreve
                # como a *natureza* foi decidida (cache/regra/manual), nao a
                # categoria; a transacao continua com natureza=gasto sabida,
                # so sem categoria (estado diferente de "pendente" de
                # natureza, que e natureza IS NULL -- research.md #12).
                "UPDATE transacao SET categoria_id = NULL WHERE categoria_id = ?",
                (categoria_id,),
            )
            conn.execute("UPDATE estabelecimento SET tipo_categoria_id = NULL WHERE tipo_categoria_id = ?", (categoria_id,))
            conn.execute("DELETE FROM cache_descricao_natureza WHERE categoria_id = ?", (categoria_id,))
            conn.execute("DELETE FROM regra_natureza WHERE categoria_id = ?", (categoria_id,))
        else:
            return False

        conn.execute("UPDATE nota_fiscal SET categoria_id = NULL WHERE categoria_id = ?", (categoria_id,))
        conn.execute("DELETE FROM categoria WHERE id = ?", (categoria_id,))
        conn.commit()
        return True
    finally:
        conn.close()


# --- Repositorio de transacao (feature 010) ------------------------------

def inserir_transacao(transacao: Transacao, db_path: str = DEFAULT_DB_PATH) -> int:
    """Insere a transacao; se o fingerprint ja existe, retorna o id ja
    existente em vez de levantar erro -- mesma semantica de idempotencia
    silenciosa que a migracao de historico de nota fiscal ja usa (FR-009,
    data-model.md)."""
    conn = get_connection(db_path)
    try:
        try:
            cursor = conn.execute(
                """
                INSERT INTO transacao (
                    fingerprint, data, descricao, descricao_normalizada, valor, tipo,
                    natureza, metodo_classificacao_natureza, categoria_id, conta, titular,
                    fonte, nota_fiscal_id, estabelecimento_id, data_importacao
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    transacao.fingerprint,
                    transacao.data,
                    transacao.descricao,
                    transacao.descricao_normalizada,
                    transacao.valor,
                    transacao.tipo.value if isinstance(transacao.tipo, TipoTransacao) else transacao.tipo,
                    transacao.natureza,
                    transacao.metodo_classificacao_natureza,
                    transacao.categoria_id,
                    transacao.conta,
                    transacao.titular,
                    transacao.fonte,
                    transacao.nota_fiscal_id,
                    transacao.estabelecimento_id,
                    transacao.data_importacao,
                ),
            )
        except sqlite3.IntegrityError:
            existente = conn.execute(
                "SELECT id FROM transacao WHERE fingerprint = ?", (transacao.fingerprint,)
            ).fetchone()
            return existente["id"]
        conn.commit()
        transacao.id = cursor.lastrowid
        return transacao.id
    finally:
        conn.close()


def buscar_transacao_por_fingerprint(fingerprint: str, db_path: str = DEFAULT_DB_PATH) -> Transacao | None:
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM transacao WHERE fingerprint = ?", (fingerprint,)).fetchone()
        return _row_to_transacao(row) if row else None
    finally:
        conn.close()


def buscar_transacao_por_id(transacao_id: int, db_path: str = DEFAULT_DB_PATH) -> Transacao | None:
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM transacao WHERE id = ?", (transacao_id,)).fetchone()
        return _row_to_transacao(row) if row else None
    finally:
        conn.close()


def buscar_transacao_por_nota_fiscal_id(nota_fiscal_id: int, db_path: str = DEFAULT_DB_PATH) -> Transacao | None:
    """A transacao reconciliada com a nota, se houver -- indice unico em
    transacao.nota_fiscal_id garante no maximo uma (US3, T028)."""
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM transacao WHERE nota_fiscal_id = ?", (nota_fiscal_id,)).fetchone()
        return _row_to_transacao(row) if row else None
    finally:
        conn.close()


def listar_transacoes(
    mes: str | None = None,
    conta: str | None = None,
    natureza: str | None = None,
    categoria_id: int | None = None,
    titular: str | None = None,
    db_path: str = DEFAULT_DB_PATH,
) -> list[Transacao]:
    """Lista transacoes ordenadas por data desc, id desc -- filtros
    opcionais por mes (AAAA-MM), conta (ja canonicalizada), natureza,
    categoria (evolucao do polimento pos-deploy: visao geral, alem da
    fila de pendentes; `categoria_id` usado para inspecionar o uso de uma
    categoria antes de exclui-la) e titular (feature 011, mesmo padrao de
    filtro ja usado em listar_notas)."""
    conn = get_connection(db_path)
    try:
        query = "SELECT * FROM transacao"
        condicoes: list[str] = []
        params: list = []
        if mes:
            condicoes.append("substr(data, 1, 7) = ?")
            params.append(mes)
        if conta:
            condicoes.append("conta = ?")
            params.append(conta)
        if natureza == "pendente":
            condicoes.append("natureza IS NULL")
        elif natureza:
            condicoes.append("natureza = ?")
            params.append(natureza)
        if categoria_id is not None:
            condicoes.append("categoria_id = ?")
            params.append(categoria_id)
        if titular:
            condicoes.append("titular = ?")
            params.append(titular)
        if condicoes:
            query += " WHERE " + " AND ".join(condicoes)
        query += " ORDER BY data DESC, id DESC"
        rows = conn.execute(query, params).fetchall()
        return [_row_to_transacao(row) for row in rows]
    finally:
        conn.close()


def listar_contas_distintas(db_path: str = DEFAULT_DB_PATH) -> list[str]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute("SELECT DISTINCT conta FROM transacao ORDER BY conta").fetchall()
        return [row["conta"] for row in rows]
    finally:
        conn.close()


def listar_estabelecimentos_nomeados(db_path: str = DEFAULT_DB_PATH) -> list[dict]:
    """Estabelecimentos ja identificados (nome_fantasia preenchido) --
    usado para sugerir nomes ja usados na fila de gerenciamento (evita
    recriar 'Letícia Arte e Talento' do zero pra cada grafia truncada
    diferente que o banco gera). Deduplicado por nome_fantasia
    (case-insensitive): se restaram registros antigos com o mesmo nome em
    linhas separadas (de antes do merge automatico existir), a sugestao
    aparece uma unica vez em vez de repetida -- bug real reportado pelo
    usuario."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT id, nome_fantasia, tipo_categoria_id FROM estabelecimento WHERE nome_fantasia IS NOT NULL ORDER BY nome_fantasia, id"
        ).fetchall()
    finally:
        conn.close()

    vistos: set[str] = set()
    resultado: list[dict] = []
    for row in rows:
        chave = row["nome_fantasia"].strip().lower()
        if chave in vistos:
            continue
        vistos.add(chave)
        resultado.append(dict(row))
    return resultado


def mapa_nomes_estabelecimentos(db_path: str = DEFAULT_DB_PATH) -> dict[int, str]:
    """id -> nome_fantasia para TODOS os estabelecimentos com nome, sem
    deduplicar por nome (ao contrario de listar_estabelecimentos_nomeados,
    que dedup para a sugestao de autocomplete) -- usado para resolver o
    nome de exibicao de qualquer transacao.estabelecimento_id, que precisa
    encontrar todo id existente, nao so um representante por nome."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT id, nome_fantasia FROM estabelecimento WHERE nome_fantasia IS NOT NULL"
        ).fetchall()
        return {row["id"]: row["nome_fantasia"] for row in rows}
    finally:
        conn.close()


def classificar_natureza_transacao(
    transacao_id: int,
    natureza: str,
    categoria_id: int | None,
    metodo: str,
    descricao_normalizada: str | None,
    db_path: str = DEFAULT_DB_PATH,
) -> None:
    """Grava a natureza (e categoria, quando gasto) de uma transacao e faz
    upsert em cache_descricao_natureza -- mesmo padrao de
    classificar_item_automaticamente (feature 008), sem tabela de historico
    dedicada (data-model.md: FR-007 exige so que a correcao manual
    prevaleca, o que o upsert de cache ja garante)."""
    conn = get_connection(db_path)
    try:
        conn.execute(
            "UPDATE transacao SET natureza = ?, categoria_id = ?, metodo_classificacao_natureza = ?, "
            "descricao_normalizada = ? WHERE id = ?",
            (natureza, categoria_id, metodo, descricao_normalizada, transacao_id),
        )
        if descricao_normalizada:
            conn.execute(
                """
                INSERT INTO cache_descricao_natureza (descricao_normalizada, natureza, categoria_id)
                VALUES (?, ?, ?)
                ON CONFLICT(descricao_normalizada) DO UPDATE SET natureza = excluded.natureza, categoria_id = excluded.categoria_id
                """,
                (descricao_normalizada, natureza, categoria_id),
            )
        conn.commit()
    finally:
        conn.close()


def listar_transacoes_pendentes_natureza(db_path: str = DEFAULT_DB_PATH) -> dict:
    """Fila de revisao de natureza (US4, FR-006) -- mesmo formato de
    listar_itens_pendentes (feature 008), agrupado por
    descricao_normalizada."""
    conn = get_connection(db_path)
    try:
        grupos = conn.execute(
            """
            SELECT descricao_normalizada, COUNT(*) AS quantidade_transacoes, MIN(id) AS exemplo_transacao_id
            FROM transacao
            WHERE natureza IS NULL AND descricao_normalizada IS NOT NULL
            GROUP BY descricao_normalizada
            ORDER BY quantidade_transacoes DESC
            """
        ).fetchall()
        total_pendente = conn.execute("SELECT COUNT(*) FROM transacao WHERE natureza IS NULL").fetchone()[0]
        total_transacoes = conn.execute("SELECT COUNT(*) FROM transacao").fetchone()[0]
        return {
            "resumo": {"total_pendente": total_pendente, "total_transacoes": total_transacoes},
            "grupos": [
                {
                    "descricao_normalizada": row["descricao_normalizada"],
                    "quantidade_transacoes": row["quantidade_transacoes"],
                    "exemplo_transacao_id": row["exemplo_transacao_id"],
                }
                for row in grupos
            ],
        }
    finally:
        conn.close()


def classificar_grupo_pendente_natureza(
    descricao_normalizada: str, natureza: str, categoria_id: int | None, db_path: str = DEFAULT_DB_PATH
) -> int:
    """Classifica em lote todas as transacoes pendentes com a mesma
    descricao_normalizada numa unica acao (US4, FR-006). Retorna a
    quantidade de transacoes afetadas."""
    conn = get_connection(db_path)
    try:
        ids = [
            row["id"]
            for row in conn.execute(
                "SELECT id FROM transacao WHERE descricao_normalizada = ? AND natureza IS NULL",
                (descricao_normalizada,),
            ).fetchall()
        ]
    finally:
        conn.close()

    for transacao_id in ids:
        classificar_natureza_transacao(
            transacao_id, natureza, categoria_id, "manual", descricao_normalizada, db_path=db_path
        )
    return len(ids)


def atribuir_natureza_manual(
    transacao_id: int, natureza: str, categoria_id: int | None, db_path: str = DEFAULT_DB_PATH
) -> bool | None:
    """Correcao manual de uma transacao especifica (US4, FR-007). Retorna
    None se a transacao nao existe; False se natureza for invalida; True em
    sucesso. A correcao prevalece sobre classificacao automatica anterior e
    passa a valer para transacoes futuras da mesma descricao (upsert de
    cache)."""
    if natureza not in NATUREZAS_VALIDAS:
        return False

    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT descricao_normalizada FROM transacao WHERE id = ?", (transacao_id,)
        ).fetchone()
        if row is None:
            return None
        descricao_normalizada = row["descricao_normalizada"]
    finally:
        conn.close()

    classificar_natureza_transacao(
        transacao_id, natureza, categoria_id, "manual", descricao_normalizada, db_path=db_path
    )
    return True


# --- Reconciliacao Nota Fiscal <-> Transacao (feature 010) ---------------

def buscar_notas_candidatas_reconciliacao(
    transacao_id: int, janela_dias: int, db_path: str = DEFAULT_DB_PATH
) -> list[dict]:
    """Notas fiscais candidatas a reconciliar com a transacao: mesmo valor,
    data de emissao dentro da janela (nota emitida antes ou no mesmo dia da
    transacao, ate `janela_dias` depois), e ainda nao reconciliada com
    nenhuma outra transacao (research.md #3/#7)."""
    conn = get_connection(db_path)
    try:
        transacao = conn.execute("SELECT * FROM transacao WHERE id = ?", (transacao_id,)).fetchone()
        if transacao is None:
            return []
        rows = conn.execute(
            """
            SELECT nf.id AS nota_fiscal_id, nf.data_emissao, nf.valor_total, nf.emitente_nome
            FROM nota_fiscal nf
            WHERE nf.valor_total = ?
              AND nf.data_emissao IS NOT NULL
              AND date(nf.data_emissao) <= date(?)
              AND date(nf.data_emissao) >= date(?, ?)
              AND nf.id NOT IN (SELECT nota_fiscal_id FROM transacao WHERE nota_fiscal_id IS NOT NULL)
            """,
            (
                transacao["valor"],
                transacao["data"],
                transacao["data"],
                f"-{janela_dias} days",
            ),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def reconciliar_transacao(transacao_id: int, janela_dias: int, db_path: str = DEFAULT_DB_PATH) -> str:
    """Aplica research.md #7: exatamente um candidato -> liga
    automaticamente ('reconciliada'); mais de um -> nenhum vinculo
    automatico ('ambigua'); nenhum -> ('sem_candidato')."""
    candidatos = buscar_notas_candidatas_reconciliacao(transacao_id, janela_dias, db_path=db_path)
    if len(candidatos) == 1:
        conn = get_connection(db_path)
        try:
            conn.execute(
                "UPDATE transacao SET nota_fiscal_id = ? WHERE id = ?",
                (candidatos[0]["nota_fiscal_id"], transacao_id),
            )
            conn.commit()
        finally:
            conn.close()
        return "reconciliada"
    if len(candidatos) > 1:
        return "ambigua"
    return "sem_candidato"


def listar_reconciliacoes_pendentes(db_path: str = DEFAULT_DB_PATH) -> list[dict]:
    """Fila de casos ambiguos (US3, FR-013) -- recalculada ao vivo (mesmo
    espirito de research.md #8: sem estado persistido de 'ambiguo')."""
    from src.services.conta_canonica import eh_conta_debito

    conn = get_connection(db_path)
    try:
        pendentes = conn.execute(
            "SELECT id, conta FROM transacao WHERE natureza = 'gasto' AND nota_fiscal_id IS NULL"
        ).fetchall()
    finally:
        conn.close()

    casos: dict[int, dict] = {}
    for row in pendentes:
        janela = 3 if eh_conta_debito(row["conta"]) else 45
        candidatos = buscar_notas_candidatas_reconciliacao(row["id"], janela, db_path=db_path)
        if len(candidatos) <= 1:
            continue
        for candidato in candidatos:
            nota_id = candidato["nota_fiscal_id"]
            caso = casos.setdefault(nota_id, {"nota_fiscal_id": nota_id, "candidatos": []})
            caso["candidatos"].append(
                {
                    "transacao_id": row["id"],
                    "valor": candidato["valor_total"],
                }
            )
    return list(casos.values())


def vincular_reconciliacao_manual(
    transacao_id: int, nota_fiscal_id: int, db_path: str = DEFAULT_DB_PATH
) -> bool | None:
    """Resolve manualmente um caso ambiguo, ou cria um vinculo onde a
    automatica nao encontrou nada (US3). Retorna None se a transacao ou a
    nota nao existem; False se a nota ja esta vinculada a outra transacao;
    True em sucesso."""
    conn = get_connection(db_path)
    try:
        transacao_existe = conn.execute("SELECT 1 FROM transacao WHERE id = ?", (transacao_id,)).fetchone()
        nota_existe = conn.execute("SELECT 1 FROM nota_fiscal WHERE id = ?", (nota_fiscal_id,)).fetchone()
        if transacao_existe is None or nota_existe is None:
            return None

        try:
            conn.execute(
                "UPDATE transacao SET nota_fiscal_id = ? WHERE id = ?", (nota_fiscal_id, transacao_id)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            return False
        return True
    finally:
        conn.close()


def desvincular_reconciliacao(transacao_id: int, db_path: str = DEFAULT_DB_PATH) -> bool | None:
    """Desfaz uma reconciliacao, automatica ou manual (FR-014). Retorna
    None se a transacao nao existe ou nao tem nota vinculada; True em
    sucesso."""
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT nota_fiscal_id FROM transacao WHERE id = ?", (transacao_id,)).fetchone()
        if row is None or row["nota_fiscal_id"] is None:
            return None
        conn.execute("UPDATE transacao SET nota_fiscal_id = NULL WHERE id = ?", (transacao_id,))
        conn.commit()
        return True
    finally:
        conn.close()


# --- Repositorio de estabelecimento (feature 010) -------------------------

def buscar_estabelecimento_por_id(estabelecimento_id: int, db_path: str = DEFAULT_DB_PATH) -> Estabelecimento | None:
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM estabelecimento WHERE id = ?", (estabelecimento_id,)).fetchone()
        return _row_to_estabelecimento(row) if row else None
    finally:
        conn.close()


def obter_ou_criar_estabelecimento_por_documento(documento: str, db_path: str = DEFAULT_DB_PATH) -> int:
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT id FROM estabelecimento WHERE documento = ?", (documento,)).fetchone()
        if row is not None:
            return row["id"]
        cursor = conn.execute("INSERT INTO estabelecimento (documento) VALUES (?)", (documento,))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def obter_ou_criar_estabelecimento_por_descricao(descricao_normalizada: str, db_path: str = DEFAULT_DB_PATH) -> int:
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT id FROM estabelecimento WHERE descricao_normalizada = ? AND documento IS NULL",
            (descricao_normalizada,),
        ).fetchone()
        if row is not None:
            return row["id"]
        cursor = conn.execute(
            "INSERT INTO estabelecimento (descricao_normalizada) VALUES (?)", (descricao_normalizada,)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def buscar_estabelecimento_id_por_descricao(descricao_normalizada: str, db_path: str = DEFAULT_DB_PATH) -> int | None:
    """So busca, nunca cria -- usado antes de criar um estabelecimento por
    documento (research.md #9) pra checar se a MESMA descricao exata ja
    tem um estabelecimento por descricao, e nesse caso promove ele em vez
    de deixar duas identidades pro mesmo lugar (bug real: uma transacao
    reconciliada com nota que traz CNPJ criava um estabelecimento novo
    mesmo quando outra transacao igualzinha, sem nota, ja tinha resolvido
    por descricao)."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT id FROM estabelecimento WHERE descricao_normalizada = ? AND documento IS NULL",
            (descricao_normalizada,),
        ).fetchone()
        return row["id"] if row else None
    finally:
        conn.close()


def promover_estabelecimento_para_documento(
    estabelecimento_id: int, documento: str, db_path: str = DEFAULT_DB_PATH
) -> int:
    """Quando um estabelecimento identificado por descricao ganha um
    documento (CNPJ/CPF) depois -- ex.: a transacao reconcilia com uma nota
    que traz CNPJ (FR-019) -- unifica com o estabelecimento ja existente
    por aquele documento, se houver, em vez de manter duas identidades.
    Retorna o id do estabelecimento definitivo (pode ser um id diferente do
    informado, quando ha fusao)."""
    conn = get_connection(db_path)
    try:
        existente = conn.execute("SELECT id FROM estabelecimento WHERE documento = ?", (documento,)).fetchone()
        if existente is not None and existente["id"] != estabelecimento_id:
            conn.execute(
                "UPDATE transacao SET estabelecimento_id = ? WHERE estabelecimento_id = ?",
                (existente["id"], estabelecimento_id),
            )
            conn.execute("DELETE FROM estabelecimento WHERE id = ?", (estabelecimento_id,))
            conn.commit()
            return existente["id"]

        conn.execute("UPDATE estabelecimento SET documento = ? WHERE id = ?", (documento, estabelecimento_id))
        conn.commit()
        return estabelecimento_id
    finally:
        conn.close()


def vincular_transacao_a_estabelecimento(transacao_id: int, estabelecimento_id: int, db_path: str = DEFAULT_DB_PATH) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            "UPDATE transacao SET estabelecimento_id = ? WHERE id = ?", (estabelecimento_id, transacao_id)
        )
        conn.commit()
    finally:
        conn.close()


def listar_estabelecimentos_pendentes(db_path: str = DEFAULT_DB_PATH) -> list[dict]:
    """Fila de gerenciamento (US5, FR-018) -- estabelecimentos ainda sem
    nome_fantasia, com a contagem de transacoes vinculadas e um exemplo de
    descricao real de uma delas. O exemplo existe pra tornar reconhecivel
    um estabelecimento identificado por CNPJ/CPF (research.md #9) -- sem
    ele, a fila so mostrava o documento cru, sem nenhuma pista de qual
    loja e (bug relatado pelo usuario: nao reconhecia uma compra no
    Varejao porque ela tinha sido resolvida por CNPJ, nao por descricao)."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT e.id, e.documento, e.descricao_normalizada, COUNT(t.id) AS quantidade_transacoes,
                   MAX(t.descricao) AS exemplo_descricao
            FROM estabelecimento e
            LEFT JOIN transacao t ON t.estabelecimento_id = e.id
            WHERE e.nome_fantasia IS NULL
            GROUP BY e.id
            ORDER BY quantidade_transacoes DESC
            """
        ).fetchall()
        return [
            {
                "id": row["id"],
                "chave": row["documento"] or row["descricao_normalizada"],
                "tipo_chave": "documento" if row["documento"] else "descricao",
                "quantidade_transacoes": row["quantidade_transacoes"],
                "exemplo_descricao": row["exemplo_descricao"],
            }
            for row in rows
        ]
    finally:
        conn.close()


def atribuir_estabelecimento(
    estabelecimento_id: int, nome_fantasia: str, tipo_categoria_id: int | None, db_path: str = DEFAULT_DB_PATH
) -> bool | None:
    """Atribui nome fantasia e tipo. Quando o nome informado (case-
    insensitive) ja pertence a OUTRO estabelecimento, funde os dois em
    vez de criar uma segunda identidade com o mesmo nome (bug real
    reportado pelo usuario: grafias truncadas diferentes do banco para o
    mesmo lugar geravam duplicata visivel na sugestao de nomes). Mesmo
    padrao de promover_estabelecimento_para_documento, so que chaveado
    por nome em vez de CNPJ/CPF."""
    conn = get_connection(db_path)
    try:
        existe = conn.execute("SELECT 1 FROM estabelecimento WHERE id = ?", (estabelecimento_id,)).fetchone()
        if existe is None:
            return None

        duplicata = conn.execute(
            "SELECT id, tipo_categoria_id FROM estabelecimento WHERE lower(nome_fantasia) = lower(?) AND id != ?",
            (nome_fantasia, estabelecimento_id),
        ).fetchone()

        if duplicata is not None:
            id_definitivo = duplicata["id"]
            tipo_final = tipo_categoria_id if tipo_categoria_id is not None else duplicata["tipo_categoria_id"]
            conn.execute(
                "UPDATE estabelecimento SET tipo_categoria_id = ? WHERE id = ?", (tipo_final, id_definitivo)
            )
            conn.execute(
                "UPDATE transacao SET estabelecimento_id = ? WHERE estabelecimento_id = ?",
                (id_definitivo, estabelecimento_id),
            )
            conn.execute("DELETE FROM estabelecimento WHERE id = ?", (estabelecimento_id,))
            conn.commit()
            return True

        conn.execute(
            # COALESCE preserva o tipo ja existente quando tipo_categoria_id
            # nao e informado (None) -- necessario pro atalho de editar so o
            # nome fantasia a partir do detalhe da nota (nota_detalhe.html)
            # nao apagar um tipo ja atribuido antes por outro caminho.
            "UPDATE estabelecimento SET nome_fantasia = ?, tipo_categoria_id = COALESCE(?, tipo_categoria_id) WHERE id = ?",
            (nome_fantasia, tipo_categoria_id, estabelecimento_id),
        )
        conn.commit()
        return True
    finally:
        conn.close()
