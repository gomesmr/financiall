from __future__ import annotations

import os

from src.storage import db as storage_db


def excluir_nota_fiscal(nota_id: int, db_path: str = storage_db.DEFAULT_DB_PATH) -> bool:
    """Exclui a nota (banco) e depois tenta remover os arquivos dos envios
    associados do disco, best-effort (research.md #2 - falha ao remover um
    arquivo ja ausente nao e erro e nao desfaz a exclusao do banco).
    Retorna False se a nota nao existia; True em caso de sucesso."""
    caminhos = storage_db.excluir_nota(nota_id, db_path=db_path)
    if caminhos is None:
        return False

    for caminho in caminhos:
        try:
            os.remove(caminho)
        except FileNotFoundError:
            pass

    return True
