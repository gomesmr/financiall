from __future__ import annotations

import argparse
import sys

from src.services.importar_historico_extrato import ArquivoExtratoError, importar_historico_extrato
from src.storage import db as storage_db


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Importa o histórico de transações de extrato (registro.json legado) para o financiALL."
    )
    parser.add_argument("arquivo", help="Caminho do arquivo de histórico (registro.json)")
    parser.add_argument("--db-path", dest="db_path", default=storage_db.DEFAULT_DB_PATH, help="Banco de destino")
    args = parser.parse_args(argv)

    storage_db.init_db(args.db_path)

    try:
        resumo = importar_historico_extrato(args.arquivo, db_path=args.db_path)
    except ArquivoExtratoError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(
        f"Importação concluída: {resumo.importadas} transação(ões) importada(s), "
        f"{resumo.ja_existentes} já existente(s) na base, "
        f"{resumo.puladas} registro(s) pulado(s) por dado inválido."
    )
    print(
        f"Classificação automática: {resumo.classificadas_automaticamente} por cache/regra, "
        f"{resumo.pendentes_natureza} pendente(s) de revisão."
    )
    print(
        f"Reconciliação: {resumo.reconciliadas} transação(ões) ligada(s) a nota fiscal, "
        f"{resumo.ambiguas} caso(s) ambíguo(s) na fila de revisão."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
