from __future__ import annotations

from datetime import date

import pytest

from src.models.item_nota import ItemNota
from src.models.nota_fiscal import CanalOrigem, NotaFiscal, StatusNota
from src.services import resumo
from src.storage import db as storage_db
from tests.helpers import gerar_chave_valida


@pytest.fixture()
def db_path(tmp_path):
    caminho = str(tmp_path / "financiall.db")
    storage_db.init_db(caminho)
    return caminho


def _gravar_nota(db_path, data_emissao, valor_total, numero="000000099"):
    nota = NotaFiscal(
        canal_origem=CanalOrigem.URL_CHAVE,
        status=StatusNota.COMPLETA if valor_total is not None else StatusNota.PENDENTE_REVISAO,
        chave_acesso=gerar_chave_valida(numero=numero),
        data_emissao=data_emissao,
        valor_total=valor_total,
    )
    storage_db.inserir_nota(nota, db_path=db_path)
    return nota


def _mes_corrente_como_data(dia: str) -> str:
    hoje = date.today()
    return f"{hoje.year:04d}-{hoje.month:02d}-{dia}"


def _gravar_item(db_path, nota_fiscal_id, valor_total_item, categoria_id=None):
    storage_db.inserir_itens(
        [ItemNota(nota_fiscal_id=nota_fiscal_id, descricao="item de teste", valor_total_item=valor_total_item)],
        db_path=db_path,
    )
    itens = storage_db.listar_itens_por_nota(nota_fiscal_id, db_path=db_path)
    item = itens[-1]
    if categoria_id is not None:
        storage_db.atribuir_categoria_manual(item.id, categoria_id, db_path=db_path)
    return item


def test_gasto_mes_corrente_soma_em_centavos_ignorando_nulos(db_path):
    _gravar_nota(db_path, _mes_corrente_como_data("05"), 1000, numero="000000001")
    _gravar_nota(db_path, _mes_corrente_como_data("10"), 2550, numero="000000002")
    _gravar_nota(db_path, _mes_corrente_como_data("15"), None, numero="000000003")  # pendente, sem total

    resultado = resumo.gasto_mes_corrente(db_path=db_path)

    assert resultado is not None
    assert resultado.total_gasto == 3550
    assert resultado.quantidade_notas == 3  # inclui a pendente de revisao na contagem


def test_gasto_mes_corrente_sem_notas_retorna_none(db_path):
    assert resumo.gasto_mes_corrente(db_path=db_path) is None


def test_historico_meses_anteriores_nao_inclui_mes_corrente(db_path):
    _gravar_nota(db_path, _mes_corrente_como_data("05"), 1000, numero="000000004")
    _gravar_nota(db_path, "2025-01-10", 5000, numero="000000005")
    _gravar_nota(db_path, "2025-02-15", 3000, numero="000000006")

    historico = resumo.historico_meses_anteriores(db_path=db_path)

    meses = [r.mes for r in historico]
    assert resumo.mes_atual() not in meses
    assert "2025-01" in meses
    assert "2025-02" in meses


def test_historico_meses_anteriores_ordenado_do_mais_recente_para_o_mais_antigo(db_path):
    _gravar_nota(db_path, "2025-01-10", 1000, numero="000000007")
    _gravar_nota(db_path, "2025-03-10", 2000, numero="000000008")
    _gravar_nota(db_path, "2025-02-10", 3000, numero="000000009")

    historico = resumo.historico_meses_anteriores(db_path=db_path)

    assert [r.mes for r in historico] == ["2025-03", "2025-02", "2025-01"]


def test_historico_vazio_quando_nenhuma_nota_de_mes_anterior(db_path):
    _gravar_nota(db_path, _mes_corrente_como_data("05"), 1000, numero="000000010")
    assert resumo.historico_meses_anteriores(db_path=db_path) == []


# --- feature 005/009: gasto por tipo de estabelecimento --------------------


def test_gasto_por_estabelecimento_soma_por_categoria(db_path):
    categoria_id = storage_db.criar_categoria("Alimentação", db_path=db_path)
    nota_1 = _gravar_nota(db_path, "2025-06-05", 1000, numero="000000011")
    nota_2 = _gravar_nota(db_path, "2025-06-10", 2000, numero="000000012")
    storage_db.atribuir_categoria_a_nota(nota_1.id, categoria_id, db_path=db_path)
    storage_db.atribuir_categoria_a_nota(nota_2.id, categoria_id, db_path=db_path)

    resultado = resumo.gasto_por_estabelecimento("2025-06", db_path=db_path)

    assert len(resultado) == 1
    assert resultado[0].categoria_id == categoria_id
    assert resultado[0].nome == "Alimentação"
    assert resultado[0].total_gasto == 3000


def test_gasto_por_estabelecimento_agrupa_notas_sem_categoria(db_path):
    categoria_id = storage_db.criar_categoria("Transporte", db_path=db_path)
    nota_com_categoria = _gravar_nota(db_path, "2025-06-05", 1000, numero="000000013")
    _gravar_nota(db_path, "2025-06-06", 500, numero="000000014")  # sem categoria
    storage_db.atribuir_categoria_a_nota(nota_com_categoria.id, categoria_id, db_path=db_path)

    resultado = resumo.gasto_por_estabelecimento("2025-06", db_path=db_path)

    por_nome = {g.nome: g for g in resultado}
    assert por_nome["Transporte"].total_gasto == 1000
    assert por_nome["Sem categoria"].categoria_id is None
    assert por_nome["Sem categoria"].total_gasto == 500


def test_gasto_por_estabelecimento_exclui_nota_com_valor_total_nulo(db_path):
    _gravar_nota(db_path, "2025-06-05", None, numero="000000015")  # pendente, sem total

    resultado = resumo.gasto_por_estabelecimento("2025-06", db_path=db_path)

    assert resultado == []


def test_gasto_por_estabelecimento_ordenado_do_maior_para_o_menor(db_path):
    categoria_pequena = storage_db.criar_categoria("Lazer", db_path=db_path)
    categoria_grande = storage_db.criar_categoria("Supermercado", db_path=db_path)
    nota_pequena = _gravar_nota(db_path, "2025-06-05", 500, numero="000000016")
    nota_grande = _gravar_nota(db_path, "2025-06-06", 5000, numero="000000017")
    storage_db.atribuir_categoria_a_nota(nota_pequena.id, categoria_pequena, db_path=db_path)
    storage_db.atribuir_categoria_a_nota(nota_grande.id, categoria_grande, db_path=db_path)

    resultado = resumo.gasto_por_estabelecimento("2025-06", db_path=db_path)

    assert [g.nome for g in resultado] == ["Supermercado", "Lazer"]


def test_gasto_por_estabelecimento_nivel_1_agrupa_subcategoria_no_pai(db_path):
    saude = storage_db.criar_categoria("Saúde", db_path=db_path)
    dentista = storage_db.criar_categoria("Dentista", parent_id=saude, db_path=db_path)
    plano = storage_db.criar_categoria("Plano de Saúde", parent_id=saude, db_path=db_path)
    nota_dentista = _gravar_nota(db_path, "2025-06-05", 1000, numero="000000018")
    nota_plano = _gravar_nota(db_path, "2025-06-06", 2000, numero="000000019")
    storage_db.atribuir_categoria_a_nota(nota_dentista.id, dentista, db_path=db_path)
    storage_db.atribuir_categoria_a_nota(nota_plano.id, plano, db_path=db_path)

    resultado_nivel_1 = resumo.gasto_por_estabelecimento("2025-06", nivel=1, db_path=db_path)
    resultado_nivel_2 = resumo.gasto_por_estabelecimento("2025-06", nivel=2, db_path=db_path)

    assert len(resultado_nivel_1) == 1
    assert resultado_nivel_1[0].nome == "Saúde"
    assert resultado_nivel_1[0].total_gasto == 3000

    por_nome_nivel_2 = {g.nome: g.total_gasto for g in resultado_nivel_2}
    assert por_nome_nivel_2 == {"Dentista": 1000, "Plano de Saúde": 2000}


# --- feature 009 (US1): gasto por categoria do item, com fallback ----------


def test_gasto_por_categoria_item_separa_por_categoria_do_item(db_path):
    alimentacao = storage_db.criar_categoria("Alimentação", db_path=db_path)
    higiene = storage_db.criar_categoria("Higiene pessoal e perfumaria", db_path=db_path)
    nota = _gravar_nota(db_path, "2025-06-05", 3000, numero="100000001")
    _gravar_item(db_path, nota.id, 2000, categoria_id=alimentacao)
    _gravar_item(db_path, nota.id, 1000, categoria_id=higiene)

    resultado = resumo.gasto_por_categoria_item("2025-06", db_path=db_path)

    por_nome = {g.nome: g for g in resultado}
    assert por_nome["Alimentação"].total_gasto == 2000
    assert por_nome["Higiene pessoal e perfumaria"].total_gasto == 1000
    assert "Sem categoria" not in por_nome


def test_gasto_por_categoria_item_fallback_para_categoria_da_nota_sem_item_classificado(db_path):
    estabelecimento = storage_db.criar_categoria("Supermercado", db_path=db_path)
    nota = _gravar_nota(db_path, "2025-06-05", 1500, numero="100000002")
    storage_db.atribuir_categoria_a_nota(nota.id, estabelecimento, db_path=db_path)
    _gravar_item(db_path, nota.id, 1500, categoria_id=None)  # item ainda pendente

    resultado = resumo.gasto_por_categoria_item("2025-06", db_path=db_path)

    assert len(resultado) == 1
    assert resultado[0].nome == "Supermercado"
    assert resultado[0].total_gasto == 1500


def test_gasto_por_categoria_item_nota_sem_itens_usa_categoria_da_nota(db_path):
    saude = storage_db.criar_categoria("Saúde", db_path=db_path)
    nota = _gravar_nota(db_path, "2025-06-05", 800, numero="100000003")
    storage_db.atribuir_categoria_a_nota(nota.id, saude, db_path=db_path)

    resultado = resumo.gasto_por_categoria_item("2025-06", db_path=db_path)

    assert len(resultado) == 1
    assert resultado[0].nome == "Saúde"
    assert resultado[0].total_gasto == 800


def test_gasto_por_categoria_item_pendente_em_nota_ja_classificada_vira_sem_categoria(db_path):
    alimentacao = storage_db.criar_categoria("Alimentação", db_path=db_path)
    estabelecimento = storage_db.criar_categoria("Supermercado", db_path=db_path)
    nota = _gravar_nota(db_path, "2025-06-05", 2500, numero="100000004")
    storage_db.atribuir_categoria_a_nota(nota.id, estabelecimento, db_path=db_path)
    _gravar_item(db_path, nota.id, 1500, categoria_id=alimentacao)
    _gravar_item(db_path, nota.id, 1000, categoria_id=None)  # pendente

    resultado = resumo.gasto_por_categoria_item("2025-06", db_path=db_path)

    por_nome = {g.nome: g for g in resultado}
    assert por_nome["Alimentação"].total_gasto == 1500
    assert por_nome["Sem categoria"].total_gasto == 1000
    assert "Supermercado" not in por_nome  # a nota tem item classificado, nao cai no fallback


def test_gasto_por_categoria_item_exclui_item_com_valor_nulo(db_path):
    alimentacao = storage_db.criar_categoria("Alimentação", db_path=db_path)
    nota = _gravar_nota(db_path, "2025-06-05", 1000, numero="100000005")
    _gravar_item(db_path, nota.id, 1000, categoria_id=alimentacao)
    _gravar_item(db_path, nota.id, None, categoria_id=alimentacao)

    resultado = resumo.gasto_por_categoria_item("2025-06", db_path=db_path)

    assert len(resultado) == 1
    assert resultado[0].total_gasto == 1000


def test_gasto_por_categoria_item_nivel_1_agrupa_por_categoria_de_topo(db_path):
    alimentacao = storage_db.criar_categoria("Alimentação", db_path=db_path)
    biscoitos = storage_db.criar_categoria("Biscoitos", parent_id=alimentacao, db_path=db_path)
    lanche = storage_db.criar_categoria("Lanche", parent_id=alimentacao, db_path=db_path)
    nota = _gravar_nota(db_path, "2025-06-05", 3000, numero="100000006")
    _gravar_item(db_path, nota.id, 1000, categoria_id=biscoitos)
    _gravar_item(db_path, nota.id, 2000, categoria_id=lanche)

    resultado_nivel_1 = resumo.gasto_por_categoria_item("2025-06", nivel=1, db_path=db_path)
    resultado_nivel_2 = resumo.gasto_por_categoria_item("2025-06", nivel=2, db_path=db_path)

    assert len(resultado_nivel_1) == 1
    assert resultado_nivel_1[0].nome == "Alimentação"
    assert resultado_nivel_1[0].total_gasto == 3000

    por_nome_nivel_2 = {g.nome: g.total_gasto for g in resultado_nivel_2}
    assert por_nome_nivel_2 == {"Biscoitos": 1000, "Lanche": 2000}


# --- feature 009 (US2): navegacao por mes -----------------------------------


def test_listar_meses_com_notas_ordenado_do_mais_recente(db_path):
    _gravar_nota(db_path, "2025-01-10", 1000, numero="200000001")
    _gravar_nota(db_path, "2025-03-10", 2000, numero="200000002")
    _gravar_nota(db_path, "2025-02-10", 3000, numero="200000003")

    assert resumo.listar_meses_com_notas(db_path=db_path) == ["2025-03", "2025-02", "2025-01"]


def test_listar_meses_com_notas_vazio_sem_nenhuma_nota(db_path):
    assert resumo.listar_meses_com_notas(db_path=db_path) == []


def test_resumo_de_mes_encontra_o_mes_pedido(db_path):
    _gravar_nota(db_path, "2025-02-10", 1500, numero="200000004")
    _gravar_nota(db_path, "2025-02-20", 500, numero="200000005")

    resultado = resumo.resumo_de_mes("2025-02", db_path=db_path)

    assert resultado is not None
    assert resultado.total_gasto == 2000
    assert resultado.quantidade_notas == 2


def test_resumo_de_mes_none_quando_mes_nao_tem_nota(db_path):
    _gravar_nota(db_path, "2025-02-10", 1000, numero="200000006")
    assert resumo.resumo_de_mes("2025-05", db_path=db_path) is None


# --- feature 009 (US4): notas agrupadas por mes -----------------------------


def test_agrupar_notas_por_mes_preserva_ordem_mes_mais_recente_primeiro(db_path):
    _gravar_nota(db_path, "2025-01-10", 1000, numero="300000001")
    _gravar_nota(db_path, "2025-03-05", 2000, numero="300000002")
    _gravar_nota(db_path, "2025-03-20", 3000, numero="300000003")

    notas = storage_db.listar_notas(db_path=db_path)
    grupos = resumo.agrupar_notas_por_mes(notas)

    assert [mes for mes, _ in grupos] == ["2025-03", "2025-01"]
    assert len(grupos[0][1]) == 2
    assert len(grupos[1][1]) == 1


def test_agrupar_notas_por_mes_lista_vazia(db_path):
    assert resumo.agrupar_notas_por_mes([]) == []


# --- feature 010: gasto do mes sem dupla contagem (US3) ---------------------

from src.models.transacao import Transacao, TipoTransacao  # noqa: E402


def _gravar_transacao(
    db_path, data, valor, natureza="gasto", categoria_id=None, nota_fiscal_id=None, fingerprint=None, descricao_normalizada=None
):
    transacao = Transacao(
        fingerprint=fingerprint or f"fp-{data}-{valor}-{natureza}-{nota_fiscal_id}",
        data=data,
        descricao="transacao de teste",
        descricao_normalizada=descricao_normalizada,
        valor=valor,
        tipo=TipoTransacao.SAIDA,
        conta="itau_2486",
        natureza=natureza,
        categoria_id=categoria_id,
        nota_fiscal_id=nota_fiscal_id,
    )
    transacao_id = storage_db.inserir_transacao(transacao, db_path=db_path)
    return transacao_id


def test_gasto_mes_soma_transacao_gasto_junto_com_notas(db_path):
    _gravar_nota(db_path, _mes_corrente_como_data("05"), 1000, numero="400000001")
    _gravar_transacao(db_path, _mes_corrente_como_data("06"), 2000)

    resultado = resumo.gasto_mes_corrente(db_path=db_path)

    assert resultado.total_gasto == 3000
    assert resultado.quantidade_notas == 2


def test_gasto_mes_nota_reconciliada_nao_soma_duas_vezes(db_path):
    nota = _gravar_nota(db_path, _mes_corrente_como_data("05"), 1500, numero="400000002")
    _gravar_transacao(db_path, _mes_corrente_como_data("06"), 1500, nota_fiscal_id=nota.id)

    resultado = resumo.gasto_mes_corrente(db_path=db_path)

    # soma so uma vez (pela transacao) -- se a nota tambem contasse, daria 3000
    assert resultado.total_gasto == 1500


def test_gasto_mes_desvincular_reconciliacao_passa_a_contar_as_duas_separadamente(db_path):
    """FR-014/US3 cenário 5: desfazer uma reconciliação errada faz a
    transação e a nota voltarem a ser contadas SEPARADAMENTE -- se elas de
    fato representam compras diferentes (o motivo de ser um erro desfazer),
    o total sobe de volta a refletir as duas, em vez de ficar preso ao
    valor único que a reconciliação (incorreta) produzia."""
    nota = _gravar_nota(db_path, _mes_corrente_como_data("05"), 1500, numero="400000003")
    transacao_id = _gravar_transacao(db_path, _mes_corrente_como_data("06"), 1500, nota_fiscal_id=nota.id)

    antes = resumo.gasto_mes_corrente(db_path=db_path).total_gasto
    storage_db.desvincular_reconciliacao(transacao_id, db_path=db_path)
    depois = resumo.gasto_mes_corrente(db_path=db_path).total_gasto

    assert antes == 1500  # enquanto reconciliadas, soma uma unica vez
    assert depois == 3000  # desvinculadas, cada uma soma pela sua propria fonte


def test_gasto_mes_transacao_natureza_diferente_de_gasto_nao_soma(db_path):
    _gravar_transacao(db_path, _mes_corrente_como_data("06"), 5000, natureza="renda")
    _gravar_transacao(db_path, _mes_corrente_como_data("07"), 200, natureza="pagamento_fatura")
    _gravar_transacao(db_path, _mes_corrente_como_data("08"), 300, natureza="transferencia_interna")

    resultado = resumo.gasto_mes_corrente(db_path=db_path)

    assert resultado is None  # nenhuma transacao de natureza=gasto, nenhuma nota


def test_gasto_por_categoria_item_transacao_sem_nota_usa_categoria_propria(db_path):
    categoria_id = storage_db.criar_categoria("Transporte", db_path=db_path)
    _gravar_transacao(db_path, _mes_corrente_como_data("06"), 2500, categoria_id=categoria_id)

    resultado = resumo.gasto_por_categoria_item(resumo.mes_atual(), db_path=db_path)

    assert len(resultado) == 1
    assert resultado[0].categoria_id == categoria_id
    assert resultado[0].total_gasto == 2500


def test_gasto_por_categoria_item_transacao_reconciliada_usa_itens_da_nota(db_path):
    categoria_item = storage_db.criar_categoria("Alimentação", db_path=db_path)
    nota = _gravar_nota(db_path, _mes_corrente_como_data("05"), 1000, numero="400000004")
    _gravar_item(db_path, nota.id, 1000, categoria_id=categoria_item)
    _gravar_transacao(db_path, _mes_corrente_como_data("06"), 1000, nota_fiscal_id=nota.id)

    resultado = resumo.gasto_por_categoria_item(resumo.mes_atual(), db_path=db_path)

    assert len(resultado) == 1
    assert resultado[0].categoria_id == categoria_item
    assert resultado[0].total_gasto == 1000


def test_gasto_por_categoria_item_transacao_reconciliada_sem_item_usa_categoria_da_transacao(db_path):
    categoria_transacao = storage_db.criar_categoria("Saúde", db_path=db_path)
    nota = _gravar_nota(db_path, _mes_corrente_como_data("05"), 800, numero="400000005")
    _gravar_transacao(db_path, _mes_corrente_como_data("06"), 800, categoria_id=categoria_transacao, nota_fiscal_id=nota.id)

    resultado = resumo.gasto_por_categoria_item(resumo.mes_atual(), db_path=db_path)

    assert len(resultado) == 1
    assert resultado[0].categoria_id == categoria_transacao
    assert resultado[0].total_gasto == 800


# --- feature 010 (US5): gasto por estabelecimento inclui transacao sem nota -


def test_gasto_por_estabelecimento_inclui_transacao_sem_nota(db_path):
    tipo_id = storage_db.criar_categoria("Supermercado", db_path=db_path)
    from src.services import estabelecimento as estabelecimento_service

    transacao_id = _gravar_transacao(db_path, _mes_corrente_como_data("06"), 2000, descricao_normalizada="MERCADO DA ESQUINA")
    estabelecimento_id = estabelecimento_service.resolver_estabelecimento(transacao_id, db_path=db_path)
    storage_db.atribuir_estabelecimento(estabelecimento_id, "Mercado da Esquina", tipo_id, db_path=db_path)

    resultado = resumo.gasto_por_estabelecimento(resumo.mes_atual(), db_path=db_path)

    assert len(resultado) == 1
    assert resultado[0].categoria_id == tipo_id
    assert resultado[0].total_gasto == 2000


def test_gasto_por_estabelecimento_transacao_com_nota_nao_soma_duas_vezes(db_path):
    """A nota ja conta pelo eixo nota_fiscal.categoria_id -- a transacao
    reconciliada com ela nao deve somar de novo (FR-020)."""
    tipo_nota_id = storage_db.criar_categoria("Farmácia", db_path=db_path)
    nota = _gravar_nota(db_path, _mes_corrente_como_data("05"), 1200, numero="400000006")
    storage_db.atribuir_categoria_a_nota(nota.id, tipo_nota_id, db_path=db_path)
    _gravar_transacao(db_path, _mes_corrente_como_data("06"), 1200, nota_fiscal_id=nota.id)

    resultado = resumo.gasto_por_estabelecimento(resumo.mes_atual(), db_path=db_path)

    assert len(resultado) == 1
    assert resultado[0].categoria_id == tipo_nota_id
    assert resultado[0].total_gasto == 1200


# --- polimento pos-deploy: saldo do mes e agrupamento de transacoes --------


def test_saldo_do_mes_soma_entradas_e_saidas(db_path):
    _gravar_transacao(db_path, _mes_corrente_como_data("05"), 500000, natureza="renda")
    _gravar_transacao(db_path, _mes_corrente_como_data("06"), 150000)  # gasto

    saldo = resumo.saldo_do_mes(resumo.mes_atual(), db_path=db_path)

    assert saldo.total_entradas == 500000
    assert saldo.total_saidas == 150000
    assert saldo.saldo == 350000


def test_saldo_do_mes_ignora_pagamento_fatura_transferencia_e_estorno(db_path):
    _gravar_transacao(db_path, _mes_corrente_como_data("05"), 500000, natureza="renda")
    _gravar_transacao(db_path, _mes_corrente_como_data("06"), 200000, natureza="pagamento_fatura")
    _gravar_transacao(db_path, _mes_corrente_como_data("07"), 30000, natureza="transferencia_interna")
    _gravar_transacao(db_path, _mes_corrente_como_data("08"), 1000, natureza="estorno_credito")

    saldo = resumo.saldo_do_mes(resumo.mes_atual(), db_path=db_path)

    assert saldo.total_entradas == 500000
    assert saldo.total_saidas == 0
    assert saldo.saldo == 500000


def test_saldo_do_mes_sem_nenhuma_transacao_e_zero(db_path):
    saldo = resumo.saldo_do_mes("2020-01", db_path=db_path)
    assert saldo == resumo.SaldoMes(mes="2020-01", total_entradas=0, total_saidas=0, saldo=0)


def test_agrupar_transacoes_por_mes_mes_mais_recente_primeiro(db_path):
    t1 = _gravar_transacao(db_path, "2026-01-10", 1000, fingerprint="fp-jan")
    t2 = _gravar_transacao(db_path, "2026-03-05", 2000, fingerprint="fp-mar-1")
    t3 = _gravar_transacao(db_path, "2026-03-20", 3000, fingerprint="fp-mar-2")

    transacoes = storage_db.listar_transacoes(db_path=db_path)
    grupos = resumo.agrupar_transacoes_por_mes(transacoes)

    assert [mes for mes, _ in grupos] == ["2026-03", "2026-01"]
    assert len(grupos[0][1]) == 2
    assert len(grupos[1][1]) == 1


def test_listar_transacoes_filtra_por_natureza_pendente(db_path):
    _gravar_transacao(db_path, "2026-04-01", 1000, natureza=None, fingerprint="fp-pendente")
    _gravar_transacao(db_path, "2026-04-02", 2000, natureza="gasto", fingerprint="fp-gasto")

    resultado = storage_db.listar_transacoes(natureza="pendente", db_path=db_path)

    assert len(resultado) == 1
    assert resultado[0].natureza is None
