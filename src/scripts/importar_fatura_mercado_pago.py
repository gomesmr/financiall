from __future__ import annotations

import argparse
import os
import sys

from src.services.importar_fatura_mercado_pago import parsear
from src.services.importar_historico_extrato import processar_transacoes
from src.storage import db as storage_db


def _listar_arquivos_pdf(caminho: str) -> list[str]:
    if os.path.isdir(caminho):
        return sorted(
            os.path.join(caminho, nome) for nome in os.listdir(caminho) if nome.lower().endswith(".pdf")
        )
    return [caminho]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Importa fatura(s) de cartão Mercado Pago (.pdf) para o financiALL, de forma recorrente."
    )
    parser.add_argument("caminho", help="Arquivo .pdf ou pasta com faturas")
    parser.add_argument("--db-path", dest="db_path", default=storage_db.DEFAULT_DB_PATH, help="Banco de destino")
    args = parser.parse_args(argv)

    storage_db.init_db(args.db_path)

    arquivos = _listar_arquivos_pdf(args.caminho)
    if not arquivos or not os.path.isfile(arquivos[0]):
        print(f"Arquivo não encontrado: {args.caminho}", file=sys.stderr)
        return 1

    resumo_total = None
    for arquivo in arquivos:
        try:
            registros = parsear(arquivo)
        except Exception as exc:  # arquivo corrompido/formato inesperado (Princípio III)
            print(f"Não foi possível interpretar o arquivo '{arquivo}': {exc}", file=sys.stderr)
            return 1

        resumo = processar_transacoes(registros, db_path=args.db_path)
        if resumo_total is None:
            resumo_total = resumo
        else:
            resumo_total.importadas += resumo.importadas
            resumo_total.ja_existentes += resumo.ja_existentes
            resumo_total.puladas += resumo.puladas
            resumo_total.classificadas_automaticamente += resumo.classificadas_automaticamente
            resumo_total.pendentes_natureza += resumo.pendentes_natureza
            resumo_total.reconciliadas += resumo.reconciliadas
            resumo_total.ambiguas += resumo.ambiguas

    print(
        f"Importação concluída: {resumo_total.importadas} transação(ões) importada(s), "
        f"{resumo_total.ja_existentes} já existente(s) na base, "
        f"{resumo_total.puladas} registro(s) pulado(s) por dado inválido."
    )
    print(
        f"Classificação automática: {resumo_total.classificadas_automaticamente} por cache/regra, "
        f"{resumo_total.pendentes_natureza} pendente(s) de revisão."
    )
    print(
        f"Reconciliação: {resumo_total.reconciliadas} transação(ões) ligada(s) a nota fiscal, "
        f"{resumo_total.ambiguas} caso(s) ambíguo(s) na fila de revisão."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
