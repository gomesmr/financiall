from __future__ import annotations

from src.storage import db as storage_db


def validar_e_criar_categoria(nome: str, db_path: str = storage_db.DEFAULT_DB_PATH) -> tuple[int | None, str | None]:
    """Recusa nome vazio/so espacos (FR-010) antes de tentar gravar;
    delega a checagem de duplicata ao indice unico do repositorio
    (FR-002). Retorna (id, None) em sucesso ou (None, mensagem)."""
    if not nome or not nome.strip():
        return None, "Informe um nome para a categoria."

    categoria_id = storage_db.criar_categoria(nome, db_path=db_path)
    if categoria_id is None:
        return None, "Já existe uma categoria com esse nome."
    return categoria_id, None


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
