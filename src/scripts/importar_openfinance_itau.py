from __future__ import annotations

import argparse
import os
import sys

from src.services.importar_historico_extrato import processar_transacoes
from src.services.importar_openfinance_itau import parsear
from src.storage import db as storage_db


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Importa um dump JSON de dados do Open Finance Itau (contas + faturas de cartao, "
            "gerado por uma sessao do Claude via MCP cumbuca-openfinance) para o financiALL."
        )
    )
    parser.add_argument("caminho", help="Arquivo .json com o dump do Open Finance")
    parser.add_argument("--db-path", dest="db_path", default=storage_db.DEFAULT_DB_PATH, help="Banco de destino")
    args = parser.parse_args(argv)

    if not os.path.isfile(args.caminho):
        print(f"Arquivo não encontrado: {args.caminho}", file=sys.stderr)
        return 1

    storage_db.init_db(args.db_path)

    try:
        registros = parsear(args.caminho)
    except Exception as exc:  # arquivo corrompido/formato inesperado (Principio III)
        print(f"Não foi possível interpretar o arquivo '{args.caminho}': {exc}", file=sys.stderr)
        return 1

    resumo = processar_transacoes(registros, db_path=args.db_path)

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
