from __future__ import annotations

from src.models.categoria import Categoria
from src.storage import db as storage_db


def _nome_normalizado(nome: str) -> str:
    return nome.strip().casefold()


def _buscar_quase_duplicata(nome: str, parent_id: int | None, db_path: str) -> Categoria | None:
    """Compara `nome` contra as demais categorias do MESMO nivel (topo
    global, ou subcategorias do mesmo `parent_id` -- research.md #19):
    prefixo/substring simples, suficiente para o volume de uma taxonomia
    pessoal (plan.md). Match exato nao conta -- ja e barrado pelo indice
    unico, tratado como duplicata (nao quase-duplicata)."""
    nome_normalizado = _nome_normalizado(nome)
    for candidata in storage_db.listar_categorias(db_path=db_path):
        if candidata.parent_id != parent_id:
            continue
        candidata_normalizada = _nome_normalizado(candidata.nome)
        if candidata_normalizada == nome_normalizado:
            continue
        if candidata_normalizada in nome_normalizado or nome_normalizado in candidata_normalizada:
            return candidata
    return None


def validar_e_criar_categoria(
    nome: str,
    parent_id: int | None = None,
    forcar: bool = False,
    db_path: str = storage_db.DEFAULT_DB_PATH,
) -> tuple[int | None, str | None, dict | None]:
    """Recusa nome vazio/so espacos (FR-010) e parent_id invalido antes de
    tentar gravar; detecta quase-duplicata escopada pelo mesmo nivel do
    indice unico (research.md #19) e, quando nao `forcar`, devolve um
    aviso em vez de criar (FR-002) -- o cliente decide usar a sugestao ou
    reenviar com `forcar=True`. Retorna (id, None, None) em sucesso,
    (None, mensagem, None) em erro de validacao/duplicata exata, (None,
    None, aviso) em quase-duplicata nao forcada."""
    if not nome or not nome.strip():
        return None, "Informe um nome para a categoria.", None

    if parent_id is not None:
        categoria_pai = storage_db.buscar_categoria_por_id(parent_id, db_path=db_path)
        if categoria_pai is None:
            return None, "Categoria pai não encontrada.", None
        if categoria_pai.parent_id is not None:
            return None, "Categoria pai não pode ser uma subcategoria.", None

    if not forcar:
        quase_duplicata = _buscar_quase_duplicata(nome, parent_id, db_path=db_path)
        if quase_duplicata is not None:
            return (
                None,
                None,
                {
                    "aviso": "Já existe uma categoria parecida.",
                    "sugestao": {"id": quase_duplicata.id, "nome": quase_duplicata.nome},
                },
            )

    categoria_id = storage_db.criar_categoria(nome, parent_id=parent_id, db_path=db_path)
    if categoria_id is None:
        return None, "Já existe uma categoria com esse nome.", None
    return categoria_id, None, None


def validar_e_editar_categoria(
    categoria_id: int, novo_nome: str, db_path: str = storage_db.DEFAULT_DB_PATH
) -> tuple[bool | None, str | None]:
    """Mesma validacao de validar_e_criar_categoria, para edicao.
    Retorna (True, None) em sucesso, (None, mensagem) se a categoria nao
    existe, (False, mensagem) se o nome e invalido/duplicado."""
    if not novo_nome or not novo_nome.strip():
        return False, "Informe um nome para a categoria."

    resultado = storage_db.editar_categoria(categoria_id, novo_nome, db_path=db_path)
    if resultado is None:
        return None, "Categoria não encontrada."
    if resultado is False:
        return False, "Já existe uma categoria com esse nome."
    return True, None
