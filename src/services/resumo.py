from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.storage import db as storage_db


@dataclass(frozen=True)
class ResumoMes:
    mes: str
    total_gasto: int | None
    quantidade_notas: int


@dataclass(frozen=True)
class GastoCategoria:
    categoria_id: int | None  # None = "sem categoria"
    nome: str
    total_gasto: int


def mes_atual() -> str:
    hoje = date.today()
    return f"{hoje.year:04d}-{hoje.month:02d}"


def _bucket_por_nivel(
    categoria_id: int | None, nivel: int, categorias_por_id: dict
) -> tuple[int | None, str]:
    """Resolve o par (categoria_id, nome) usado para agrupar um gasto dado o
    nivel escolhido -- nivel 1 agrupa pela categoria de topo (resolve o pai
    quando a categoria e uma subcategoria); nivel 2 usa a categoria tal como
    esta atribuida. categoria_id=None (ou categoria inexistente) sempre vira
    o bucket "Sem categoria" (feature 009, data-model.md)."""
    if categoria_id is None:
        return (None, "Sem categoria")
    categoria = categorias_por_id.get(categoria_id)
    if categoria is None:
        return (None, "Sem categoria")
    if nivel == 1 and categoria.parent_id is not None:
        pai = categorias_por_id.get(categoria.parent_id)
        if pai is not None:
            return (pai.id, pai.nome)
    return (categoria.id, categoria.nome)


def listar_meses_com_notas(db_path: str = storage_db.DEFAULT_DB_PATH) -> list[str]:
    """Meses (AAAA-MM) que tem pelo menos uma nota, do mais recente para o
    mais antigo (US2, FR-004) -- base da navegacao por mes do resumo."""
    return [r.mes for r in _query_resumo_por_mes(db_path)]


def resumo_de_mes(mes: str, db_path: str = storage_db.DEFAULT_DB_PATH) -> ResumoMes | None:
    """Total e quantidade de notas de um mes qualquer (US2) -- None se o mes
    nao tem nenhuma nota."""
    for resumo in _query_resumo_por_mes(db_path):
        if resumo.mes == mes:
            return resumo
    return None


def _mes_da_nota(nota) -> str:
    if nota.data_emissao:
        return nota.data_emissao[:7]
    if nota.ano_mes_emissao:
        return f"20{nota.ano_mes_emissao[:2]}-{nota.ano_mes_emissao[2:4]}"
    return "Sem data"


def agrupar_notas_por_mes(notas: list) -> list[tuple[str, list]]:
    """Agrupa notas (ja ordenadas por mes desc, id desc -- storage_db.listar_notas)
    em secoes por mes, mes mais recente primeiro (US4, FR-007). Assume a
    ordenacao ja existente da query -- so consolida linhas consecutivas do
    mesmo mes, sem SQL novo (research.md #6). Nota sem data_emissao nem
    ano_mes_emissao agrupa sob "Sem data"."""
    grupos: list[tuple[str, list]] = []
    mes_atual_do_grupo: str | None = None
    notas_do_grupo: list = []
    for nota in notas:
        mes = _mes_da_nota(nota)
        if mes != mes_atual_do_grupo:
            if notas_do_grupo:
                grupos.append((mes_atual_do_grupo, notas_do_grupo))
            mes_atual_do_grupo = mes
            notas_do_grupo = []
        notas_do_grupo.append(nota)
    if notas_do_grupo:
        grupos.append((mes_atual_do_grupo, notas_do_grupo))
    return grupos


def _query_resumo_por_mes(db_path: str) -> list[ResumoMes]:
    """Agrupa por mês e soma o gasto (feature 010, research.md #8): notas
    fiscais que NAO estao reconciliadas com nenhuma transacao (fonte de
    verdade do valor ainda e a propria nota) + transacoes com
    natureza='gasto' (fonte de verdade do valor quando existe extrato).
    Uma nota reconciliada nunca soma aqui -- so a transacao correspondente
    soma, evitando contar a mesma compra duas vezes (FR-015/016). Calculado
    ao vivo a cada chamada, sem tabela de cache. `quantidade_notas` passa a
    contar a quantidade combinada de lancamentos (nota nao reconciliada +
    transacao de gasto) que compoem o total do mes."""
    conn = storage_db.get_connection(db_path)
    try:
        rows = conn.execute(
            """
            WITH combinado AS (
                SELECT
                    COALESCE(substr(data_emissao, 1, 7), '20' || substr(ano_mes_emissao, 1, 2) || '-' || substr(ano_mes_emissao, 3, 2)) AS mes,
                    valor_total AS valor
                FROM nota_fiscal
                WHERE id NOT IN (SELECT nota_fiscal_id FROM transacao WHERE nota_fiscal_id IS NOT NULL)
                UNION ALL
                SELECT substr(data, 1, 7) AS mes, valor
                FROM transacao
                WHERE natureza = 'gasto'
            )
            SELECT mes, SUM(valor) AS total_gasto, COUNT(*) AS quantidade_notas
            FROM combinado
            WHERE mes IS NOT NULL
            GROUP BY mes
            ORDER BY mes DESC
            """
        ).fetchall()
        return [
            ResumoMes(mes=row["mes"], total_gasto=row["total_gasto"], quantidade_notas=row["quantidade_notas"])
            for row in rows
        ]
    finally:
        conn.close()


def gasto_mes_corrente(db_path: str = storage_db.DEFAULT_DB_PATH) -> ResumoMes | None:
    """Total parcial do mês corrente (US7, FR-015). None se não há
    nenhuma nota com data no mês corrente."""
    mes = mes_atual()
    for resumo in _query_resumo_por_mes(db_path):
        if resumo.mes == mes:
            return resumo
    return None


def historico_meses_anteriores(db_path: str = storage_db.DEFAULT_DB_PATH) -> list[ResumoMes]:
    """Total por mês para meses anteriores ao corrente (US8, FR-016),
    ordenado do mais recente para o mais antigo."""
    mes = mes_atual()
    return [resumo for resumo in _query_resumo_por_mes(db_path) if resumo.mes < mes]


def gasto_por_categoria_item(
    mes: str, nivel: int = 1, db_path: str = storage_db.DEFAULT_DB_PATH
) -> list[GastoCategoria]:
    """Soma o gasto do mes informado (AAAA-MM) agrupado por categoria de
    consumo, combinando tres fontes sem nunca contar a mesma compra duas
    vezes (feature 010, research.md #8, data-model.md):
    1. Notas NAO reconciliadas com nenhuma transacao -- mesma logica da
       feature 008/009: item classificado soma por item; sem item
       classificado, o valor total da nota cai na categoria da propria
       nota (ou "Sem categoria").
    2. Transacoes de gasto reconciliadas com uma nota -- usam os itens
       dessa nota quando classificados (mesmo racional acima); sem item
       classificado, usam a categoria da propria transacao.
    3. Transacoes de gasto sem nenhuma nota associada -- somam pela
       categoria da transacao (ou "Sem categoria").
    Item/transacao com valor nulo nunca contribui para nenhuma soma."""
    conn = storage_db.get_connection(db_path)
    try:
        linhas_notas = conn.execute(
            """
            SELECT
                nf.id AS nota_id,
                nf.categoria_id AS nota_categoria_id,
                nf.valor_total AS nota_valor_total,
                it.categoria_id AS item_categoria_id,
                it.valor_total_item AS item_valor_total
            FROM nota_fiscal nf
            LEFT JOIN item_nota it ON it.nota_fiscal_id = nf.id
            WHERE COALESCE(substr(nf.data_emissao, 1, 7), '20' || substr(nf.ano_mes_emissao, 1, 2) || '-' || substr(nf.ano_mes_emissao, 3, 2)) = ?
              AND nf.valor_total IS NOT NULL
              AND nf.id NOT IN (SELECT nota_fiscal_id FROM transacao WHERE nota_fiscal_id IS NOT NULL)
            """,
            (mes,),
        ).fetchall()

        linhas_transacoes_reconciliadas = conn.execute(
            """
            SELECT
                t.id AS transacao_id,
                t.categoria_id AS transacao_categoria_id,
                t.valor AS transacao_valor,
                it.categoria_id AS item_categoria_id,
                it.valor_total_item AS item_valor_total
            FROM transacao t
            LEFT JOIN item_nota it ON it.nota_fiscal_id = t.nota_fiscal_id
            WHERE substr(t.data, 1, 7) = ? AND t.natureza = 'gasto' AND t.nota_fiscal_id IS NOT NULL
            """,
            (mes,),
        ).fetchall()

        linhas_transacoes_sem_nota = conn.execute(
            """
            SELECT categoria_id AS transacao_categoria_id, valor AS transacao_valor
            FROM transacao
            WHERE substr(data, 1, 7) = ? AND natureza = 'gasto' AND nota_fiscal_id IS NULL
            """,
            (mes,),
        ).fetchall()
    finally:
        conn.close()

    categorias_por_id = {c.id: c for c in storage_db.listar_categorias(db_path=db_path)}

    acumulado: dict[int | None, list] = {}

    def _somar(categoria_id: int | None, valor: int) -> None:
        bucket_id, nome = _bucket_por_nivel(categoria_id, nivel, categorias_por_id)
        atual = acumulado.get(bucket_id)
        if atual is None:
            acumulado[bucket_id] = [nome, valor]
        else:
            atual[1] += valor

    por_nota: dict[int, list] = {}
    for row in linhas_notas:
        por_nota.setdefault(row["nota_id"], []).append(row)
    for linhas in por_nota.values():
        tem_item_classificado = any(linha["item_categoria_id"] is not None for linha in linhas)
        if tem_item_classificado:
            for linha in linhas:
                if linha["item_valor_total"] is None:
                    continue
                _somar(linha["item_categoria_id"], linha["item_valor_total"])
        else:
            primeira = linhas[0]
            _somar(primeira["nota_categoria_id"], primeira["nota_valor_total"])

    por_transacao: dict[int, list] = {}
    for row in linhas_transacoes_reconciliadas:
        por_transacao.setdefault(row["transacao_id"], []).append(row)
    for linhas in por_transacao.values():
        tem_item_classificado = any(linha["item_categoria_id"] is not None for linha in linhas)
        if tem_item_classificado:
            for linha in linhas:
                if linha["item_valor_total"] is None:
                    continue
                _somar(linha["item_categoria_id"], linha["item_valor_total"])
        else:
            primeira = linhas[0]
            _somar(primeira["transacao_categoria_id"], primeira["transacao_valor"])

    for row in linhas_transacoes_sem_nota:
        _somar(row["transacao_categoria_id"], row["transacao_valor"])

    resultado = [
        GastoCategoria(categoria_id=cat_id, nome=nome, total_gasto=total)
        for cat_id, (nome, total) in acumulado.items()
    ]
    resultado.sort(key=lambda g: g.total_gasto, reverse=True)
    return resultado


def gasto_por_estabelecimento(
    mes: str, nivel: int = 1, db_path: str = storage_db.DEFAULT_DB_PATH
) -> list[GastoCategoria]:
    """Soma o valor_total das notas do mes informado (AAAA-MM), agrupado
    pelo tipo de estabelecimento da nota (nota_fiscal.categoria_id,
    feature 003/009) -- eixo independente da categoria do item (US5).
    Notas sem tipo de estabelecimento agrupam sob "Sem categoria" (FR-002);
    notas com valor_total nulo sao excluidas da soma (mesma regra de
    _query_resumo_por_mes). nivel 1 resolve subcategoria -> categoria-pai
    (ex.: Saude > Dentista some sob Saude); nivel 2 usa a categoria tal
    como esta atribuida. Ordenado do maior para o menor gasto."""
    conn = storage_db.get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT nota_fiscal.categoria_id AS categoria_id, nota_fiscal.valor_total AS total_gasto
            FROM nota_fiscal
            WHERE COALESCE(substr(nota_fiscal.data_emissao, 1, 7), '20' || substr(nota_fiscal.ano_mes_emissao, 1, 2) || '-' || substr(nota_fiscal.ano_mes_emissao, 3, 2)) = ?
              AND nota_fiscal.valor_total IS NOT NULL
            """,
            (mes,),
        ).fetchall()
    finally:
        conn.close()

    categorias_por_id = {c.id: c for c in storage_db.listar_categorias(db_path=db_path)}

    acumulado: dict[int | None, list] = {}
    for row in rows:
        bucket_id, nome = _bucket_por_nivel(row["categoria_id"], nivel, categorias_por_id)
        atual = acumulado.get(bucket_id)
        if atual is None:
            acumulado[bucket_id] = [nome, row["total_gasto"]]
        else:
            atual[1] += row["total_gasto"]

    resultado = [
        GastoCategoria(categoria_id=cat_id, nome=nome, total_gasto=total)
        for cat_id, (nome, total) in acumulado.items()
    ]
    resultado.sort(key=lambda g: g.total_gasto, reverse=True)
    return resultado
