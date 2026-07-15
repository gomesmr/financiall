from __future__ import annotations

import argparse
import sys

from src.services.importar_historico import ArquivoHistoricoError, importar_historico
from src.storage import db as storage_db


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Importa o histórico de notas fiscais de um arquivo JSON legado para o financiALL."
    )
    parser.add_argument("arquivo", help="Caminho do arquivo de histórico (JSON)")
    parser.add_argument("--db-path", dest="db_path", default=storage_db.DEFAULT_DB_PATH, help="Banco de destino")
    args = parser.parse_args(argv)

    storage_db.init_db(args.db_path)

    try:
        resumo = importar_historico(args.arquivo, db_path=args.db_path)
    except ArquivoHistoricoError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(
        f"Importação concluída: {resumo.importadas} nota(s) importada(s), "
        f"{resumo.ja_existentes} já existente(s) na base, "
        f"{resumo.puladas} registro(s) pulado(s) por dado inválido."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
