"""Migracao pontual: agrupa estabelecimentos (documento IS NULL) que so
diferem pelo sufixo de parcela na descricao_normalizada (ex.:
"CLARICELL 09/21" e "CLARICELL PARCELA 12 DE 21" -> "CLARICELL") e funde
num so, atualizando a descricao_normalizada do sobrevivente pra chave ja
normalizada -- assim resolver_estabelecimento passa a encontrar o mesmo
registro em importacoes futuras (ver services/normalizacao.py:
normalizar_chave_estabelecimento). Idempotente: rodar de novo nao tem
efeito colateral (nao ha mais duplicata pra fundir depois da primeira
passada)."""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict

from src.services.normalizacao import normalizar_chave_estabelecimento
from src.storage import db as storage_db


def consolidar(db_path: str) -> dict:
    conn = storage_db.get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT id, descricao_normalizada, nome_fantasia FROM estabelecimento WHERE documento IS NULL"
        ).fetchall()

        grupos: dict[str, list] = defaultdict(list)
        for row in rows:
            if not row["descricao_normalizada"]:
                continue
            chave = normalizar_chave_estabelecimento(row["descricao_normalizada"])
            grupos[chave].append(row)

        fundidos = 0
        grupos_afetados = 0
        for chave, membros in grupos.items():
            if len(membros) < 2:
                # so precisa atualizar a descricao_normalizada armazenada se
                # ja nao estiver na forma canonica (sem sufixo de parcela)
                unico = membros[0]
                if unico["descricao_normalizada"] != chave:
                    conn.execute(
                        "UPDATE estabelecimento SET descricao_normalizada = ? WHERE id = ?",
                        (chave, unico["id"]),
                    )
                continue

            # escolhe o sobrevivente: prioriza quem ja tem nome_fantasia,
            # senao o de menor id (mais antigo)
            nomeados = [m for m in membros if m["nome_fantasia"] is not None]
            sobrevivente = nomeados[0] if nomeados else min(membros, key=lambda m: m["id"])

            # apaga os outros membros do grupo ANTES de renomear o
            # sobrevivente pra chave canonica -- se outro membro ja tivesse
            # exatamente essa forma (ex.: "CLARICELL" sem sufixo, sem ter
            # sido escolhido sobrevivente), atualizar o sobrevivente
            # primeiro colidia por um instante com o indice unico parcial
            # (achado rodando contra o banco real de producao).
            for membro in membros:
                if membro["id"] == sobrevivente["id"]:
                    continue
                conn.execute(
                    "UPDATE transacao SET estabelecimento_id = ? WHERE estabelecimento_id = ?",
                    (sobrevivente["id"], membro["id"]),
                )
                conn.execute("DELETE FROM estabelecimento WHERE id = ?", (membro["id"],))
                fundidos += 1
            conn.execute(
                "UPDATE estabelecimento SET descricao_normalizada = ? WHERE id = ?",
                (chave, sobrevivente["id"]),
            )
            grupos_afetados += 1

        conn.commit()
        return {"grupos_afetados": grupos_afetados, "estabelecimentos_fundidos": fundidos}
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", dest="db_path", default=storage_db.DEFAULT_DB_PATH)
    args = parser.parse_args(argv)

    resultado = consolidar(args.db_path)
    print(
        f"Consolidação concluída: {resultado['grupos_afetados']} grupo(s) de parcelas fundido(s), "
        f"{resultado['estabelecimentos_fundidos']} estabelecimento(s) duplicado(s) removido(s)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
