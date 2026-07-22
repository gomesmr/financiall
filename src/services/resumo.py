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


@dataclass(frozen=True)
class SaldoMes:
    mes: str
    total_entradas: int
    total_saidas: int
    saldo: int


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


def resumo_de_mes(
    mes: str, titular: str | None = None, db_path: str = storage_db.DEFAULT_DB_PATH
) -> ResumoMes | None:
    """Total e quantidade de notas de um mes qualquer (US2) -- None se o mes
    nao tem nenhuma nota. `titular` (feature 011) filtra por
    nota_fiscal.titular/transacao.titular; None mantem o consolidado."""
    for resumo in _query_resumo_por_mes(db_path, titular=titular):
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


def agrupar_transacoes_por_mes(transacoes: list) -> list[tuple[str, list]]:
    """Mesmo padrao de agrupar_notas_por_mes, para a listagem geral de
    transacoes (`/ver/transacoes`) -- transacao.data e sempre ISO, sem
    fallback de ano_mes_emissao necessario."""
    grupos: list[tuple[str, list]] = []
    mes_atual_do_grupo: str | None = None
    transacoes_do_grupo: list = []
    for transacao in transacoes:
        mes = transacao.data[:7] if transacao.data else "Sem data"
        if mes != mes_atual_do_grupo:
            if transacoes_do_grupo:
                grupos.append((mes_atual_do_grupo, transacoes_do_grupo))
            mes_atual_do_grupo = mes
            transacoes_do_grupo = []
        transacoes_do_grupo.append(transacao)
    if transacoes_do_grupo:
        grupos.append((mes_atual_do_grupo, transacoes_do_grupo))
    return grupos


def _query_resumo_por_mes(db_path: str, titular: str | None = None) -> list[ResumoMes]:
    """Agrupa por mês e soma o gasto (feature 010, research.md #8): notas
    fiscais que NAO estao reconciliadas com nenhuma transacao (fonte de
    verdade do valor ainda e a propria nota) + transacoes com
    natureza='gasto' (fonte de verdade do valor quando existe extrato).
    Uma nota reconciliada nunca soma aqui -- so a transacao correspondente
    soma, evitando contar a mesma compra duas vezes (FR-015/016). Calculado
    ao vivo a cada chamada, sem tabela de cache. `quantidade_notas` passa a
    contar a quantidade combinada de lancamentos (nota nao reconciliada +
    transacao de gasto) que compoem o total do mes. `titular` (feature 011)
    filtra as duas pontas do UNION por nota_fiscal.titular/transacao.titular;
    None mantem o consolidado do casal (comportamento anterior)."""
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
                  AND (? IS NULL OR titular = ?)
                UNION ALL
                SELECT substr(data, 1, 7) AS mes, valor
                FROM transacao
                WHERE natureza = 'gasto'
                  AND (? IS NULL OR titular = ?)
            )
            SELECT mes, SUM(valor) AS total_gasto, COUNT(*) AS quantidade_notas
            FROM combinado
            WHERE mes IS NOT NULL
            GROUP BY mes
            ORDER BY mes DESC
            """,
            (titular, titular, titular, titular),
        ).fetchall()
        return [
            ResumoMes(mes=row["mes"], total_gasto=row["total_gasto"], quantidade_notas=row["quantidade_notas"])
            for row in rows
        ]
    finally:
        conn.close()


def gasto_mes_corrente(titular: str | None = None, db_path: str = storage_db.DEFAULT_DB_PATH) -> ResumoMes | None:
    """Total parcial do mês corrente (US7, FR-015). None se não há
    nenhuma nota com data no mês corrente."""
    mes = mes_atual()
    for resumo in _query_resumo_por_mes(db_path, titular=titular):
        if resumo.mes == mes:
            return resumo
    return None


def historico_meses_anteriores(
    titular: str | None = None, db_path: str = storage_db.DEFAULT_DB_PATH
) -> list[ResumoMes]:
    """Total por mês para meses anteriores ao corrente (US8, FR-016),
    ordenado do mais recente para o mais antigo."""
    mes = mes_atual()
    return [resumo for resumo in _query_resumo_por_mes(db_path, titular=titular) if resumo.mes < mes]


def saldo_do_mes(
    mes: str, titular: str | None = None, db_path: str = storage_db.DEFAULT_DB_PATH
) -> SaldoMes:
    """Visão de saúde financeira do mês (polimento pós-deploy da feature
    010): entradas = soma de transação com natureza='renda'; saídas =
    o mesmo gasto combinado (transação + nota não reconciliada) que
    `resumo_de_mes` já calcula, reaproveitado aqui sem duplicar a lógica.
    `pagamento_fatura`, `transferencia_interna` e `estorno_credito` ficam
    de fora do saldo de propósito -- são movimentação interna ou correção
    de um gasto já contado, não entrada/saída real de dinheiro da casa.
    `titular` (feature 011) filtra entradas e saídas pelo mesmo titular;
    uma transferência entre o casal nunca conta aqui (natureza
    transferencia_interna), então o saldo de cada titular somado bate com o
    saldo conjunto (SC-003)."""
    conn = storage_db.get_connection(db_path)
    try:
        entradas = conn.execute(
            "SELECT COALESCE(SUM(valor), 0) FROM transacao WHERE natureza = 'renda' "
            "AND substr(data, 1, 7) = ? AND (? IS NULL OR titular = ?)",
            (mes, titular, titular),
        ).fetchone()[0]
    finally:
        conn.close()

    resumo_gasto = resumo_de_mes(mes, titular=titular, db_path=db_path)
    saidas = (resumo_gasto.total_gasto or 0) if resumo_gasto else 0

    return SaldoMes(mes=mes, total_entradas=entradas, total_saidas=saidas, saldo=entradas - saidas)


def gasto_por_categoria_item(
    mes: str, nivel: int = 1, titular: str | None = None, db_path: str = storage_db.DEFAULT_DB_PATH
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
    Item/transacao com valor nulo nunca contribui para nenhuma soma.
    `titular` (feature 011) filtra as tres fontes por
    nota_fiscal.titular/transacao.titular; None mantem o consolidado."""
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
              AND (? IS NULL OR nf.titular = ?)
            """,
            (mes, titular, titular),
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
              AND (? IS NULL OR t.titular = ?)
            """,
            (mes, titular, titular),
        ).fetchall()

        linhas_transacoes_sem_nota = conn.execute(
            """
            SELECT categoria_id AS transacao_categoria_id, valor AS transacao_valor
            FROM transacao
            WHERE substr(data, 1, 7) = ? AND natureza = 'gasto' AND nota_fiscal_id IS NULL
              AND (? IS NULL OR titular = ?)
            """,
            (mes, titular, titular),
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
    mes: str, nivel: int = 1, titular: str | None = None, db_path: str = storage_db.DEFAULT_DB_PATH
) -> list[GastoCategoria]:
    """Soma o gasto do mes informado (AAAA-MM) agrupado pelo tipo de
    estabelecimento -- eixo independente da categoria de gasto (US5).
    Duas fontes, sem sobreposicao (feature 010, FR-020): notas fiscais
    (nota_fiscal.categoria_id, feature 003/009 -- todas as notas do mes,
    reconciliadas ou nao, continuam contando aqui) + transacoes de gasto
    SEM nota associada (estabelecimento.tipo_categoria_id, resolvido pela
    cascata de identidade da feature 010). Transacoes COM nota nao entram
    de novo aqui -- a nota ja contou. Sem tipo de estabelecimento agrupa
    sob "Sem categoria" (FR-002). nivel 1 resolve subcategoria ->
    categoria-pai; nivel 2 usa a categoria tal como esta atribuida.
    Ordenado do maior para o menor gasto. `titular` (feature 011) filtra as
    duas fontes por nota_fiscal.titular/transacao.titular; None mantem o
    consolidado."""
    conn = storage_db.get_connection(db_path)
    try:
        linhas_notas = conn.execute(
            """
            SELECT nota_fiscal.categoria_id AS categoria_id, nota_fiscal.valor_total AS total_gasto
            FROM nota_fiscal
            WHERE COALESCE(substr(nota_fiscal.data_emissao, 1, 7), '20' || substr(nota_fiscal.ano_mes_emissao, 1, 2) || '-' || substr(nota_fiscal.ano_mes_emissao, 3, 2)) = ?
              AND nota_fiscal.valor_total IS NOT NULL
              AND (? IS NULL OR nota_fiscal.titular = ?)
            """,
            (mes, titular, titular),
        ).fetchall()

        linhas_transacoes_sem_nota = conn.execute(
            """
            SELECT e.tipo_categoria_id AS categoria_id, t.valor AS total_gasto
            FROM transacao t
            LEFT JOIN estabelecimento e ON e.id = t.estabelecimento_id
            WHERE substr(t.data, 1, 7) = ? AND t.natureza = 'gasto' AND t.nota_fiscal_id IS NULL
              AND (? IS NULL OR t.titular = ?)
            """,
            (mes, titular, titular),
        ).fetchall()
    finally:
        conn.close()

    categorias_por_id = {c.id: c for c in storage_db.listar_categorias(db_path=db_path)}

    acumulado: dict[int | None, list] = {}
    for row in list(linhas_notas) + list(linhas_transacoes_sem_nota):
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
