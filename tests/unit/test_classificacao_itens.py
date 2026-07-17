from __future__ import annotations

from pathlib import Path

import pytest

from src.models.item_nota import ItemNota
from src.models.nota_fiscal import CanalOrigem, NotaFiscal, StatusNota
from src.scripts.seed_taxonomia_categorizacao import seed_regras, seed_taxonomia
from src.services import classificacao_itens
from src.storage import db as storage_db
from tests.helpers import gerar_chave_valida


@pytest.fixture()
def db_path(tmp_path):
    caminho = str(tmp_path / "financiall.db")
    storage_db.init_db(caminho)
    return caminho


_contador_notas = 0


def _inserir_nota(db_path) -> int:
    global _contador_notas
    _contador_notas += 1
    nota = NotaFiscal(
        canal_origem=CanalOrigem.URL_CHAVE,
        status=StatusNota.COMPLETA,
        chave_acesso=gerar_chave_valida(numero=str(_contador_notas).zfill(9)),
    )
    return storage_db.inserir_nota(nota, db_path=db_path)


def _inserir_item(nota_id: int, descricao: str | None, db_path) -> int:
    item = ItemNota(nota_fiscal_id=nota_id, descricao=descricao)
    storage_db.inserir_itens([item], db_path=db_path)
    itens = storage_db.listar_itens_por_nota(nota_id, db_path=db_path)
    return itens[-1].id


def _historico_do_item(item_id: int, db_path) -> list[dict]:
    conn = storage_db.get_connection(db_path)
    try:
        linhas = conn.execute(
            "SELECT * FROM historico_classificacao_item WHERE item_nota_id = ?", (item_id,)
        ).fetchall()
        return [dict(l) for l in linhas]
    finally:
        conn.close()


# --- classificar_item_automaticamente: historico (FR-014) -----------------


def test_classificar_item_automaticamente_grava_historico_via_cache(db_path):
    nota_id = _inserir_nota(db_path)
    categoria_id = storage_db.criar_categoria("Alimentação", db_path=db_path)
    item_id = _inserir_item(nota_id, "REFRIGERANTE COCA COLA 2L", db_path=db_path)

    storage_db.classificar_item_automaticamente(
        item_id, categoria_id, "cache", "REFRIGERANTE COCA COLA 2L", db_path=db_path
    )

    historico = _historico_do_item(item_id, db_path)
    assert len(historico) == 1
    assert historico[0]["metodo"] == "cache"
    assert historico[0]["categoria_id_anterior"] is None
    assert historico[0]["categoria_id_nova"] == categoria_id

    item = storage_db.listar_itens_por_nota(nota_id, db_path=db_path)[0]
    assert item.categoria_id == categoria_id
    assert item.metodo_classificacao == "cache"
    assert item.descricao_normalizada == "REFRIGERANTE COCA COLA 2L"

    cache = storage_db.get_connection(db_path).execute(
        "SELECT categoria_id FROM cache_descricao_categoria WHERE descricao_normalizada = ?",
        ("REFRIGERANTE COCA COLA 2L",),
    ).fetchone()
    assert cache["categoria_id"] == categoria_id


def test_classificar_item_automaticamente_grava_historico_via_regra(db_path):
    nota_id = _inserir_nota(db_path)
    categoria_id = storage_db.criar_categoria("Higiene pessoal e perfumaria", db_path=db_path)
    item_id = _inserir_item(nota_id, "PAPEL HIGIENICO NEVE C/4", db_path=db_path)

    storage_db.classificar_item_automaticamente(
        item_id, categoria_id, "regra", "PAPEL HIGIENICO NEVE C/4", db_path=db_path
    )

    historico = _historico_do_item(item_id, db_path)
    assert len(historico) == 1
    assert historico[0]["metodo"] == "regra"
    assert historico[0]["categoria_id_anterior"] is None
    assert historico[0]["categoria_id_nova"] == categoria_id


# --- classificar_item: cascata cache -> regra -> pendente ------------------


def test_classificar_item_resolve_via_cache(db_path):
    categoria_id = storage_db.criar_categoria("Bebidas", db_path=db_path)
    conn = storage_db.get_connection(db_path)
    conn.execute(
        "INSERT INTO cache_descricao_categoria (descricao_normalizada, categoria_id) VALUES (?, ?)",
        ("REFRIGERANTE COCA COLA 2L", categoria_id),
    )
    conn.commit()
    conn.close()

    resultado_id, metodo = classificacao_itens.classificar_item("Refrigerante Coca Cola 2L", db_path=db_path)

    assert resultado_id == categoria_id
    assert metodo == "cache"


def test_classificar_item_resolve_via_regra_quando_sem_cache(db_path):
    categoria_id = storage_db.criar_categoria("Higiene pessoal e perfumaria", db_path=db_path)
    conn = storage_db.get_connection(db_path)
    conn.execute(
        "INSERT INTO regra_categoria (padrao, categoria_id, prioridade, ativa) VALUES (?, ?, 10, 1)",
        ("HIGIENICO", categoria_id),
    )
    conn.commit()
    conn.close()

    resultado_id, metodo = classificacao_itens.classificar_item("PAPEL HIGIENICO NEVE C/4", db_path=db_path)

    assert resultado_id == categoria_id
    assert metodo == "regra"


def test_classificar_item_regra_inativa_nao_e_usada(db_path):
    categoria_id = storage_db.criar_categoria("Higiene pessoal e perfumaria", db_path=db_path)
    conn = storage_db.get_connection(db_path)
    conn.execute(
        "INSERT INTO regra_categoria (padrao, categoria_id, prioridade, ativa) VALUES (?, ?, 10, 0)",
        ("HIGIENICO", categoria_id),
    )
    conn.commit()
    conn.close()

    resultado_id, metodo = classificacao_itens.classificar_item("PAPEL HIGIENICO NEVE C/4", db_path=db_path)

    assert resultado_id is None
    assert metodo is None


def test_classificar_item_sem_correspondencia_fica_pendente(db_path):
    resultado_id, metodo = classificacao_itens.classificar_item("PRODUTO NUNCA VISTO", db_path=db_path)
    assert (resultado_id, metodo) == (None, None)


@pytest.mark.parametrize("descricao", [None, "", "   "])
def test_classificar_item_descricao_vazia_fica_pendente_sem_excecao(db_path, descricao):
    resultado = classificacao_itens.classificar_item(descricao, db_path=db_path)
    assert resultado == (None, None)


# --- classificar_itens_pendentes_da_nota -----------------------------------


def test_classificar_itens_pendentes_da_nota_classifica_via_regra(db_path):
    categoria_id = storage_db.criar_categoria("Higiene pessoal e perfumaria", db_path=db_path)
    conn = storage_db.get_connection(db_path)
    conn.execute(
        "INSERT INTO regra_categoria (padrao, categoria_id, prioridade, ativa) VALUES (?, ?, 10, 1)",
        ("HIGIENICO", categoria_id),
    )
    conn.commit()
    conn.close()

    nota_id = _inserir_nota(db_path)
    item_id = _inserir_item(nota_id, "PAPEL HIGIENICO NEVE C/4", db_path=db_path)

    classificacao_itens.classificar_itens_pendentes_da_nota(nota_id, db_path=db_path)

    item = storage_db.listar_itens_por_nota(nota_id, db_path=db_path)[0]
    assert item.id == item_id
    assert item.categoria_id == categoria_id
    assert item.metodo_classificacao == "regra"
    assert item.descricao_normalizada == "PAPEL HIGIENICO NEVE C/4"


def test_classificar_itens_pendentes_da_nota_item_sem_correspondencia_fica_pendente(db_path):
    nota_id = _inserir_nota(db_path)
    _inserir_item(nota_id, "PRODUTO NUNCA VISTO", db_path=db_path)

    classificacao_itens.classificar_itens_pendentes_da_nota(nota_id, db_path=db_path)

    item = storage_db.listar_itens_por_nota(nota_id, db_path=db_path)[0]
    assert item.categoria_id is None
    assert item.metodo_classificacao is None
    assert item.descricao_normalizada == "PRODUTO NUNCA VISTO"


def test_classificar_itens_pendentes_da_nota_item_sem_descricao_fica_pendente_sem_excecao(db_path):
    nota_id = _inserir_nota(db_path)
    _inserir_item(nota_id, None, db_path=db_path)

    classificacao_itens.classificar_itens_pendentes_da_nota(nota_id, db_path=db_path)

    item = storage_db.listar_itens_por_nota(nota_id, db_path=db_path)[0]
    assert item.categoria_id is None
    assert item.metodo_classificacao is None
    assert item.descricao_normalizada is None


# --- listar_itens_pendentes (T013/T020) -------------------------------------


def test_listar_itens_pendentes_agrupa_por_descricao_normalizada(db_path):
    nota_id = _inserir_nota(db_path)
    _inserir_item(nota_id, "Refrigerante Coca Cola 2L", db_path=db_path)
    _inserir_item(nota_id, "REFRIGERANTE COCA COLA 2L", db_path=db_path)
    _inserir_item(nota_id, "Detergente Ype", db_path=db_path)
    classificacao_itens.classificar_itens_pendentes_da_nota(nota_id, db_path=db_path)

    resultado = storage_db.listar_itens_pendentes(db_path=db_path)

    assert resultado["resumo"] == {"total_pendente": 3, "total_itens": 3}
    grupos_por_descricao = {g["descricao_normalizada"]: g["quantidade_itens"] for g in resultado["grupos"]}
    assert grupos_por_descricao["REFRIGERANTE COCA COLA 2L"] == 2
    assert grupos_por_descricao["DETERGENTE YPE"] == 1


def test_listar_itens_pendentes_por_nota_nao_agrupa(db_path):
    nota_id = _inserir_nota(db_path)
    _inserir_item(nota_id, "Item A", db_path=db_path)
    _inserir_item(nota_id, "Item A", db_path=db_path)
    classificacao_itens.classificar_itens_pendentes_da_nota(nota_id, db_path=db_path)

    resultado = storage_db.listar_itens_pendentes(nota_fiscal_id=nota_id, db_path=db_path)

    assert len(resultado["itens"]) == 2
    assert "resumo" not in resultado


def test_listar_itens_pendentes_resumo_desconta_ja_classificados(db_path):
    categoria_id = storage_db.criar_categoria("Alimentação", db_path=db_path)
    nota_id = _inserir_nota(db_path)
    item_classificado_id = _inserir_item(nota_id, "Item classificado", db_path=db_path)
    _inserir_item(nota_id, "Item pendente", db_path=db_path)
    classificacao_itens.classificar_itens_pendentes_da_nota(nota_id, db_path=db_path)
    storage_db.atribuir_categoria_manual(item_classificado_id, categoria_id, db_path=db_path)

    resultado = storage_db.listar_itens_pendentes(db_path=db_path)

    assert resultado["resumo"] == {"total_pendente": 1, "total_itens": 2}


# --- atribuir_categoria_manual (T014/T020) ----------------------------------


def test_atribuir_categoria_manual_item_inexistente_retorna_none(db_path):
    resultado = storage_db.atribuir_categoria_manual(999, 1, db_path=db_path)
    assert resultado is None


def test_atribuir_categoria_manual_categoria_inexistente_retorna_false(db_path):
    nota_id = _inserir_nota(db_path)
    item_id = _inserir_item(nota_id, "Item qualquer", db_path=db_path)
    resultado = storage_db.atribuir_categoria_manual(item_id, 999, db_path=db_path)
    assert resultado is False


def test_atribuir_categoria_manual_classificacao_parcial_so_categoria(db_path):
    """Atribuir uma categoria de topo (sem subcategoria) e a classificacao
    parcial do FR-011 -- item deixa de estar pendente mesmo sem
    subcategoria."""
    categoria_topo_id = storage_db.criar_categoria("Alimentação", db_path=db_path)
    nota_id = _inserir_nota(db_path)
    item_id = _inserir_item(nota_id, "Item qualquer", db_path=db_path)
    classificacao_itens.classificar_itens_pendentes_da_nota(nota_id, db_path=db_path)

    resultado = storage_db.atribuir_categoria_manual(item_id, categoria_topo_id, db_path=db_path)

    assert resultado is True
    item = storage_db.listar_itens_por_nota(nota_id, db_path=db_path)[0]
    assert item.categoria_id == categoria_topo_id
    assert item.metodo_classificacao == "manual"


def test_atribuir_categoria_manual_grava_historico_com_categoria_anterior(db_path):
    categoria_1 = storage_db.criar_categoria("Alimentação", db_path=db_path)
    categoria_2 = storage_db.criar_categoria("Bebidas", db_path=db_path)
    nota_id = _inserir_nota(db_path)
    item_id = _inserir_item(nota_id, "Item qualquer", db_path=db_path)
    classificacao_itens.classificar_itens_pendentes_da_nota(nota_id, db_path=db_path)
    storage_db.atribuir_categoria_manual(item_id, categoria_1, db_path=db_path)

    storage_db.atribuir_categoria_manual(item_id, categoria_2, db_path=db_path)

    historico = _historico_do_item(item_id, db_path)
    assert len(historico) == 2
    assert historico[-1]["metodo"] == "manual"
    assert historico[-1]["categoria_id_anterior"] == categoria_1
    assert historico[-1]["categoria_id_nova"] == categoria_2


def test_atribuir_categoria_manual_a_item_pendente_resolve_demais_itens_da_mesma_descricao(db_path):
    """research.md #15: atribuir a UM item pendente via
    atribuir_categoria_manual (nao classificar_grupo_pendente) ja resolve
    todos os demais itens pendentes com a mesma descricao_normalizada."""
    categoria_id = storage_db.criar_categoria("Alimentação", db_path=db_path)
    nota_id = _inserir_nota(db_path)
    item_1 = _inserir_item(nota_id, "Item Repetido", db_path=db_path)
    item_2 = _inserir_item(nota_id, "ITEM REPETIDO", db_path=db_path)
    item_3 = _inserir_item(nota_id, "Item Diferente", db_path=db_path)
    classificacao_itens.classificar_itens_pendentes_da_nota(nota_id, db_path=db_path)

    storage_db.atribuir_categoria_manual(item_1, categoria_id, db_path=db_path)

    itens = {item.id: item for item in storage_db.listar_itens_por_nota(nota_id, db_path=db_path)}
    assert itens[item_1].categoria_id == categoria_id
    assert itens[item_2].categoria_id == categoria_id
    assert itens[item_3].categoria_id is None
    # cada item afetado ganha sua propria linha de historico
    assert len(_historico_do_item(item_2, db_path)) == 1


def test_corrigir_item_ja_classificado_nao_afeta_outros_da_mesma_descricao(db_path):
    """Diferente do caso acima: corrigir um item que JA estava
    classificado (US4) nunca dispara o efeito colateral de grupo."""
    categoria_1 = storage_db.criar_categoria("Alimentação", db_path=db_path)
    categoria_2 = storage_db.criar_categoria("Bebidas", db_path=db_path)
    nota_id = _inserir_nota(db_path)
    item_1 = _inserir_item(nota_id, "Item Repetido", db_path=db_path)
    item_2 = _inserir_item(nota_id, "Item Repetido", db_path=db_path)
    classificacao_itens.classificar_itens_pendentes_da_nota(nota_id, db_path=db_path)
    storage_db.atribuir_categoria_manual(item_1, categoria_1, db_path=db_path)
    storage_db.atribuir_categoria_manual(item_2, categoria_1, db_path=db_path)

    storage_db.atribuir_categoria_manual(item_1, categoria_2, db_path=db_path)

    item_2_atual = next(i for i in storage_db.listar_itens_por_nota(nota_id, db_path=db_path) if i.id == item_2)
    assert item_2_atual.categoria_id == categoria_1


# --- classificar_grupo_pendente (T014/T020) ---------------------------------


def test_classificar_grupo_pendente_categoria_inexistente_retorna_none(db_path):
    resultado = storage_db.classificar_grupo_pendente("QUALQUER", 999, db_path=db_path)
    assert resultado is None


def test_classificar_grupo_pendente_classifica_todos_os_itens_do_grupo(db_path):
    categoria_id = storage_db.criar_categoria("Alimentação", db_path=db_path)
    nota_id = _inserir_nota(db_path)
    _inserir_item(nota_id, "Item Repetido", db_path=db_path)
    _inserir_item(nota_id, "ITEM REPETIDO", db_path=db_path)
    _inserir_item(nota_id, "Item Repetido", db_path=db_path)
    classificacao_itens.classificar_itens_pendentes_da_nota(nota_id, db_path=db_path)

    quantidade = storage_db.classificar_grupo_pendente("ITEM REPETIDO", categoria_id, db_path=db_path)

    assert quantidade == 3
    for item in storage_db.listar_itens_por_nota(nota_id, db_path=db_path):
        assert item.categoria_id == categoria_id


def test_classificar_grupo_pendente_sem_itens_retorna_zero(db_path):
    categoria_id = storage_db.criar_categoria("Alimentação", db_path=db_path)
    quantidade = storage_db.classificar_grupo_pendente("DESCRICAO INEXISTENTE", categoria_id, db_path=db_path)
    assert quantidade == 0


# --- obter_evolucao_classificacao (T018/T020) -------------------------------


def test_obter_evolucao_classificacao_series_cumulativas_ordenadas(db_path):
    categoria_id = storage_db.criar_categoria("Alimentação", db_path=db_path)
    nota_1 = _inserir_nota(db_path)
    _inserir_item(nota_1, "Item 1", db_path=db_path)
    _inserir_item(nota_1, "Item 2", db_path=db_path)
    nota_2 = _inserir_nota(db_path)
    _inserir_item(nota_2, "Item 3", db_path=db_path)
    classificacao_itens.classificar_itens_pendentes_da_nota(nota_1, db_path=db_path)
    classificacao_itens.classificar_itens_pendentes_da_nota(nota_2, db_path=db_path)

    itens_nota_1 = storage_db.listar_itens_por_nota(nota_1, db_path=db_path)
    storage_db.atribuir_categoria_manual(itens_nota_1[0].id, categoria_id, db_path=db_path)

    evolucao = classificacao_itens.obter_evolucao_classificacao(db_path=db_path)

    totais = [p["total"] for p in evolucao["itens_totais"]]
    assert totais == sorted(totais)
    assert totais[-1] == 3

    classificados = [p["total"] for p in evolucao["itens_classificados"]]
    assert classificados == [1]


# --- US2: idempotencia e precedencia -----------------------------------


def test_classificar_itens_pendentes_da_nota_chamada_duas_vezes_e_idempotente(db_path):
    """FR-015: reprocessar uma nota ja classificada nao duplica linhas de
    historico nem altera a classificacao existente."""
    categoria_id = storage_db.criar_categoria("Higiene pessoal e perfumaria", db_path=db_path)
    conn = storage_db.get_connection(db_path)
    conn.execute(
        "INSERT INTO regra_categoria (padrao, categoria_id, prioridade, ativa) VALUES (?, ?, 10, 1)",
        ("HIGIENICO", categoria_id),
    )
    conn.commit()
    conn.close()

    nota_id = _inserir_nota(db_path)
    item_id = _inserir_item(nota_id, "PAPEL HIGIENICO NEVE C/4", db_path=db_path)

    classificacao_itens.classificar_itens_pendentes_da_nota(nota_id, db_path=db_path)
    item_apos_primeira = storage_db.listar_itens_por_nota(nota_id, db_path=db_path)[0]
    historico_apos_primeira = _historico_do_item(item_id, db_path)

    classificacao_itens.classificar_itens_pendentes_da_nota(nota_id, db_path=db_path)
    item_apos_segunda = storage_db.listar_itens_por_nota(nota_id, db_path=db_path)[0]
    historico_apos_segunda = _historico_do_item(item_id, db_path)

    assert item_apos_segunda.categoria_id == item_apos_primeira.categoria_id
    assert item_apos_segunda.metodo_classificacao == item_apos_primeira.metodo_classificacao
    assert len(historico_apos_segunda) == len(historico_apos_primeira) == 1


def test_corrigir_item_classificado_por_regra_sobrescreve_cache_para_novos_itens(db_path):
    """FR-012 cenario 2: corrigir manualmente um item que tinha sido
    classificado por regra sobrescreve cache_descricao_categoria -- um
    item NOVO com a mesma descricao normalizada passa a receber a
    categoria corrigida (via cache, precedencia sobre a regra antiga --
    research.md #10/#11)."""
    categoria_errada = storage_db.criar_categoria("Categoria Errada", db_path=db_path)
    categoria_correta = storage_db.criar_categoria("Categoria Correta", db_path=db_path)
    conn = storage_db.get_connection(db_path)
    conn.execute(
        "INSERT INTO regra_categoria (padrao, categoria_id, prioridade, ativa) VALUES (?, ?, 10, 1)",
        ("HIGIENICO", categoria_errada),
    )
    conn.commit()
    conn.close()

    nota_1 = _inserir_nota(db_path)
    item_1 = _inserir_item(nota_1, "PAPEL HIGIENICO NEVE C/4", db_path=db_path)
    classificacao_itens.classificar_itens_pendentes_da_nota(nota_1, db_path=db_path)
    item_1_classificado = storage_db.listar_itens_por_nota(nota_1, db_path=db_path)[0]
    assert item_1_classificado.categoria_id == categoria_errada
    assert item_1_classificado.metodo_classificacao == "regra"

    storage_db.atribuir_categoria_manual(item_1, categoria_correta, db_path=db_path)

    nota_2 = _inserir_nota(db_path)
    item_2_id = _inserir_item(nota_2, "PAPEL HIGIENICO NEVE C/4", db_path=db_path)
    classificacao_itens.classificar_itens_pendentes_da_nota(nota_2, db_path=db_path)

    item_2 = storage_db.listar_itens_por_nota(nota_2, db_path=db_path)[0]
    assert item_2.id == item_2_id
    assert item_2.categoria_id == categoria_correta
    assert item_2.metodo_classificacao == "cache"


# --- US3: prioridade e desempate de regra (T031/T032) ----------------------


def test_classificar_item_regra_mais_especifica_prioridade_maior_vence(db_path):
    """research.md #6: quando duas regras casam a mesma descrição, a de
    maior prioridade vence -- aqui, 'CANINO' (mais especifica, Pet) deve
    vencer sobre 'BISCOITO' (mais generica, Alimentação), mesmo padrão de
    curadoria usado nas regras-semente reais (T030)."""
    categoria_pet = storage_db.criar_categoria("Pet", db_path=db_path)
    categoria_alimentacao = storage_db.criar_categoria("Alimentação", db_path=db_path)
    conn = storage_db.get_connection(db_path)
    conn.execute(
        "INSERT INTO regra_categoria (padrao, categoria_id, prioridade, ativa) VALUES (?, ?, 5, 1)",
        ("BISCOITO", categoria_alimentacao),
    )
    conn.execute(
        "INSERT INTO regra_categoria (padrao, categoria_id, prioridade, ativa) VALUES (?, ?, 20, 1)",
        ("CANINO", categoria_pet),
    )
    conn.commit()
    conn.close()

    categoria_id, metodo = classificacao_itens.classificar_item("BISCOITO CANINO BANCOOK BIG", db_path=db_path)

    assert categoria_id == categoria_pet
    assert metodo == "regra"


def test_classificar_item_empate_de_prioridade_resolve_pelo_menor_id(db_path):
    """research.md #6: em empate de prioridade, vence a regra de menor
    id (mais antiga) -- comportamento deterministico."""
    categoria_1 = storage_db.criar_categoria("Categoria 1", db_path=db_path)
    categoria_2 = storage_db.criar_categoria("Categoria 2", db_path=db_path)
    conn = storage_db.get_connection(db_path)
    conn.execute(
        "INSERT INTO regra_categoria (padrao, categoria_id, prioridade, ativa) VALUES (?, ?, 10, 1)",
        ("ALFA", categoria_1),
    )
    conn.execute(
        "INSERT INTO regra_categoria (padrao, categoria_id, prioridade, ativa) VALUES (?, ?, 10, 1)",
        ("BETA", categoria_2),
    )
    conn.commit()
    conn.close()

    categoria_id, metodo = classificacao_itens.classificar_item("PRODUTO ALFA BETA", db_path=db_path)

    assert categoria_id == categoria_1
    assert metodo == "regra"


# --- US3: cascata contra o corpus real (T033) -------------------------------

_CORPUS_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "corpus_descricoes_produtos.txt"


@pytest.fixture()
def db_com_regras_semente(tmp_path):
    """Banco com a taxonomia e as regras-semente reais carregadas (T007/T030) --
    usado só pelo teste de cobertura do corpus, distinto do fixture `db_path`
    (vazio) usado pelos demais testes desta suíte."""
    caminho = str(tmp_path / "financiall.db")
    storage_db.init_db(caminho)
    seed_taxonomia(db_path=caminho)
    seed_regras(db_path=caminho)
    return caminho


def test_cascata_contra_corpus_real_registra_taxa_de_cobertura(db_com_regras_semente):
    """research.md #13: o corpus é enviesado para papel higiênico, não é
    amostra representativa de cesta de compra -- por isso este teste
    registra quantas descrições classificam via regra-semente vs. ficam
    pendentes, sem exigir 100% (T033). O piso de 250/327 é uma margem
    abaixo do valor real observado (282/327) na curadoria da T030 --
    serve para detectar regressão na cascata ou nas regras-semente, não
    para travar em um número exato."""
    with open(_CORPUS_PATH, encoding="utf-8") as f:
        descricoes = [linha.strip() for linha in f if linha.strip()]

    classificadas_via_regra = 0
    pendentes = 0
    for descricao in descricoes:
        categoria_id, metodo = classificacao_itens.classificar_item(descricao, db_path=db_com_regras_semente)
        if categoria_id is not None:
            assert metodo == "regra"
            classificadas_via_regra += 1
        else:
            pendentes += 1

    assert classificadas_via_regra + pendentes == len(descricoes)
    assert classificadas_via_regra >= 250


# --- US4: corrigir a fonte e reclassificar o passado (T037/T038/T043) ------


def test_calcular_impacto_correcao_fonte_item_inexistente_retorna_none(db_path):
    resultado = storage_db.calcular_impacto_correcao_fonte(999, db_path=db_path)
    assert resultado is None


def test_calcular_impacto_correcao_fonte_apenas_o_proprio_item(db_path):
    categoria_id = storage_db.criar_categoria("Higiene pessoal e perfumaria", db_path=db_path)
    nota_id = _inserir_nota(db_path)
    item_id = _inserir_item(nota_id, "Item Unico", db_path=db_path)
    classificacao_itens.classificar_itens_pendentes_da_nota(nota_id, db_path=db_path)
    storage_db.atribuir_categoria_manual(item_id, categoria_id, db_path=db_path)

    impacto = storage_db.calcular_impacto_correcao_fonte(item_id, db_path=db_path)

    assert impacto["descricao_normalizada"] == "ITEM UNICO"
    assert impacto["categoria_id_atual"] == categoria_id
    assert impacto["quantidade_itens_afetados"] == 1


def test_calcular_impacto_correcao_fonte_varios_itens_afetados(db_path):
    categoria_errada = storage_db.criar_categoria("Categoria Errada", db_path=db_path)
    conn = storage_db.get_connection(db_path)
    conn.execute(
        "INSERT INTO regra_categoria (padrao, categoria_id, prioridade, ativa) VALUES (?, ?, 10, 1)",
        ("HIGIENICO", categoria_errada),
    )
    conn.commit()
    conn.close()

    nota_1 = _inserir_nota(db_path)
    item_1 = _inserir_item(nota_1, "PAPEL HIGIENICO NEVE C/4", db_path=db_path)
    nota_2 = _inserir_nota(db_path)
    _inserir_item(nota_2, "PAPEL HIGIENICO NEVE C/4", db_path=db_path)
    classificacao_itens.classificar_itens_pendentes_da_nota(nota_1, db_path=db_path)
    classificacao_itens.classificar_itens_pendentes_da_nota(nota_2, db_path=db_path)

    impacto = storage_db.calcular_impacto_correcao_fonte(item_1, db_path=db_path)

    assert impacto["quantidade_itens_afetados"] == 2


def test_corrigir_fonte_e_reclassificar_item_inexistente_retorna_none(db_path):
    resultado = storage_db.corrigir_fonte_e_reclassificar(999, 1, db_path=db_path)
    assert resultado is None


def test_corrigir_fonte_e_reclassificar_atualiza_todas_as_ocorrencias_passadas(db_path):
    categoria_errada = storage_db.criar_categoria("Categoria Errada", db_path=db_path)
    categoria_correta = storage_db.criar_categoria("Categoria Correta", db_path=db_path)
    conn = storage_db.get_connection(db_path)
    conn.execute(
        "INSERT INTO regra_categoria (padrao, categoria_id, prioridade, ativa) VALUES (?, ?, 10, 1)",
        ("HIGIENICO", categoria_errada),
    )
    conn.commit()
    conn.close()

    nota_1 = _inserir_nota(db_path)
    item_1 = _inserir_item(nota_1, "PAPEL HIGIENICO NEVE C/4", db_path=db_path)
    nota_2 = _inserir_nota(db_path)
    item_2 = _inserir_item(nota_2, "PAPEL HIGIENICO NEVE C/4", db_path=db_path)
    classificacao_itens.classificar_itens_pendentes_da_nota(nota_1, db_path=db_path)
    classificacao_itens.classificar_itens_pendentes_da_nota(nota_2, db_path=db_path)

    quantidade = storage_db.corrigir_fonte_e_reclassificar(item_1, categoria_correta, db_path=db_path)

    assert quantidade == 2
    for item_id in (item_1, item_2):
        historico = _historico_do_item(item_id, db_path)
        assert historico[-1]["categoria_id_nova"] == categoria_correta
        assert historico[-1]["metodo"] == "manual"

    # cache sobrescrito -- um item NOVO com a mesma descricao ja chega correto
    nota_3 = _inserir_nota(db_path)
    item_3 = _inserir_item(nota_3, "PAPEL HIGIENICO NEVE C/4", db_path=db_path)
    classificacao_itens.classificar_itens_pendentes_da_nota(nota_3, db_path=db_path)
    item_3_atual = storage_db.listar_itens_por_nota(nota_3, db_path=db_path)[0]
    assert item_3_atual.categoria_id == categoria_correta
    assert item_3_atual.metodo_classificacao == "cache"


def test_corrigir_fonte_e_reclassificar_zero_outras_ocorrencias(db_path):
    categoria_errada = storage_db.criar_categoria("Categoria Errada", db_path=db_path)
    categoria_correta = storage_db.criar_categoria("Categoria Correta", db_path=db_path)
    nota_id = _inserir_nota(db_path)
    item_id = _inserir_item(nota_id, "Item Unico Aqui", db_path=db_path)
    classificacao_itens.classificar_itens_pendentes_da_nota(nota_id, db_path=db_path)
    storage_db.atribuir_categoria_manual(item_id, categoria_errada, db_path=db_path)

    quantidade = storage_db.corrigir_fonte_e_reclassificar(item_id, categoria_correta, db_path=db_path)

    assert quantidade == 1
