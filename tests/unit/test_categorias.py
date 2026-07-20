from __future__ import annotations

import pytest

from src.models.item_nota import ItemNota
from src.models.nota_fiscal import CanalOrigem, NotaFiscal, StatusNota
from src.services import categorias as categorias_service
from src.storage import db as storage_db
from tests.helpers import gerar_chave_valida


@pytest.fixture()
def db_path(tmp_path):
    caminho = str(tmp_path / "financiall.db")
    storage_db.init_db(caminho)
    return caminho


def _inserir_nota(db_path) -> int:
    nota = NotaFiscal(
        canal_origem=CanalOrigem.URL_CHAVE,
        status=StatusNota.COMPLETA,
        chave_acesso=gerar_chave_valida(),
    )
    return storage_db.inserir_nota(nota, db_path=db_path)


def _inserir_item(nota_id: int, descricao: str, db_path) -> int:
    item = ItemNota(nota_fiscal_id=nota_id, descricao=descricao)
    storage_db.inserir_itens([item], db_path=db_path)
    return storage_db.listar_itens_por_nota(nota_id, db_path=db_path)[-1].id


# --- US1: criar categoria -------------------------------------------------


def test_criar_categoria_nome_valido_retorna_id(db_path):
    categoria_id = storage_db.criar_categoria("Alimentação", db_path=db_path)
    assert isinstance(categoria_id, int)
    categoria = storage_db.buscar_categoria_por_id(categoria_id, db_path=db_path)
    assert categoria.nome == "Alimentação"


def test_criar_categoria_nome_vazio_retorna_none(db_path):
    assert storage_db.criar_categoria("", db_path=db_path) is None
    assert storage_db.criar_categoria("   ", db_path=db_path) is None


@pytest.mark.parametrize(
    "primeiro,segundo",
    [
        ("Alimentação", "Alimentação"),
        ("Alimentação", "alimentação"),
        ("Alimentação", "  Alimentação  "),
        ("Transporte", "TRANSPORTE"),
    ],
)
def test_criar_categoria_nome_duplicado_retorna_none(db_path, primeiro, segundo):
    assert storage_db.criar_categoria(primeiro, db_path=db_path) is not None
    assert storage_db.criar_categoria(segundo, db_path=db_path) is None
    assert len(storage_db.listar_categorias(db_path=db_path)) == 1


# --- US2: atribuir categoria a uma nota -----------------------------------


def test_atribuir_categoria_a_nota(db_path):
    nota_id = _inserir_nota(db_path)
    categoria_id = storage_db.criar_categoria("Transporte", db_path=db_path)

    resultado = storage_db.atribuir_categoria_a_nota(nota_id, categoria_id, db_path=db_path)

    assert resultado is True
    nota = storage_db.buscar_nota_por_id(nota_id, db_path=db_path)
    assert nota.categoria_id == categoria_id


def test_trocar_categoria_de_uma_nota(db_path):
    nota_id = _inserir_nota(db_path)
    categoria_1 = storage_db.criar_categoria("Transporte", db_path=db_path)
    categoria_2 = storage_db.criar_categoria("Saúde", db_path=db_path)
    storage_db.atribuir_categoria_a_nota(nota_id, categoria_1, db_path=db_path)

    storage_db.atribuir_categoria_a_nota(nota_id, categoria_2, db_path=db_path)

    nota = storage_db.buscar_nota_por_id(nota_id, db_path=db_path)
    assert nota.categoria_id == categoria_2


def test_remover_categoria_de_uma_nota(db_path):
    nota_id = _inserir_nota(db_path)
    categoria_id = storage_db.criar_categoria("Transporte", db_path=db_path)
    storage_db.atribuir_categoria_a_nota(nota_id, categoria_id, db_path=db_path)

    storage_db.atribuir_categoria_a_nota(nota_id, None, db_path=db_path)

    nota = storage_db.buscar_nota_por_id(nota_id, db_path=db_path)
    assert nota.categoria_id is None


def test_atribuir_categoria_a_nota_inexistente_retorna_none(db_path):
    categoria_id = storage_db.criar_categoria("Transporte", db_path=db_path)
    resultado = storage_db.atribuir_categoria_a_nota(999, categoria_id, db_path=db_path)
    assert resultado is None


def test_atribuir_categoria_inexistente_retorna_false(db_path):
    nota_id = _inserir_nota(db_path)
    resultado = storage_db.atribuir_categoria_a_nota(nota_id, 999, db_path=db_path)
    assert resultado is False


# --- US4: editar categoria -------------------------------------------------


def test_editar_categoria_nome_valido_atualiza(db_path):
    categoria_id = storage_db.criar_categoria("Transporte", db_path=db_path)

    resultado = storage_db.editar_categoria(categoria_id, "Transportes", db_path=db_path)

    assert resultado is True
    categoria = storage_db.buscar_categoria_por_id(categoria_id, db_path=db_path)
    assert categoria.nome == "Transportes"


def test_editar_categoria_inexistente_retorna_none(db_path):
    resultado = storage_db.editar_categoria(999, "Novo Nome", db_path=db_path)
    assert resultado is None


def test_editar_categoria_para_nome_duplicado_retorna_false(db_path):
    storage_db.criar_categoria("Transporte", db_path=db_path)
    categoria_2 = storage_db.criar_categoria("Saúde", db_path=db_path)

    resultado = storage_db.editar_categoria(categoria_2, "transporte", db_path=db_path)

    assert resultado is False
    categoria = storage_db.buscar_categoria_por_id(categoria_2, db_path=db_path)
    assert categoria.nome == "Saúde"


# --- US5: excluir categoria -------------------------------------------------


def test_excluir_categoria_sem_notas(db_path):
    categoria_id = storage_db.criar_categoria("Lazer", db_path=db_path)

    resultado = storage_db.excluir_categoria(categoria_id, db_path=db_path)

    assert resultado is True
    assert storage_db.buscar_categoria_por_id(categoria_id, db_path=db_path) is None


def test_excluir_categoria_com_notas_desassocia(db_path):
    nota_id = _inserir_nota(db_path)
    categoria_id = storage_db.criar_categoria("Lazer", db_path=db_path)
    storage_db.atribuir_categoria_a_nota(nota_id, categoria_id, db_path=db_path)

    resultado = storage_db.excluir_categoria(categoria_id, db_path=db_path)

    assert resultado is True
    nota = storage_db.buscar_nota_por_id(nota_id, db_path=db_path)
    assert nota.categoria_id is None


def test_excluir_categoria_inexistente_retorna_false(db_path):
    resultado = storage_db.excluir_categoria(999, db_path=db_path)
    assert resultado is False


# --- Foundational (T011): hierarquia (parent_id) e quase-duplicata --------


def test_criar_categoria_com_parent_id_valido_retorna_id(db_path):
    topo_id = storage_db.criar_categoria("Alimentação", db_path=db_path)

    sub_id = storage_db.criar_categoria("Mercearia seca", parent_id=topo_id, db_path=db_path)

    assert isinstance(sub_id, int)
    subcategoria = storage_db.buscar_categoria_por_id(sub_id, db_path=db_path)
    assert subcategoria.parent_id == topo_id


def test_criar_categoria_parent_id_de_subcategoria_retorna_none(db_path):
    """2 niveis fixos (research.md #3): uma subcategoria nao pode, por sua
    vez, ser parent_id de outra."""
    topo_id = storage_db.criar_categoria("Alimentação", db_path=db_path)
    sub_id = storage_db.criar_categoria("Mercearia seca", parent_id=topo_id, db_path=db_path)

    resultado = storage_db.criar_categoria("Nível 3", parent_id=sub_id, db_path=db_path)

    assert resultado is None


def test_criar_categoria_parent_id_inexistente_retorna_none(db_path):
    resultado = storage_db.criar_categoria("Mercearia seca", parent_id=999, db_path=db_path)
    assert resultado is None


def test_subcategorias_de_pais_diferentes_podem_ter_mesmo_nome(db_path):
    """Indice unico escopado por nivel (research.md #19): duas
    subcategorias de categorias-pai diferentes podem reaproveitar o mesmo
    nome, algo que o indice unico global antigo (feature 003) proibiria."""
    topo_1 = storage_db.criar_categoria("Alimentação", db_path=db_path)
    topo_2 = storage_db.criar_categoria("Higiene pessoal e perfumaria", db_path=db_path)

    sub_1 = storage_db.criar_categoria("Outros", parent_id=topo_1, db_path=db_path)
    sub_2 = storage_db.criar_categoria("Outros", parent_id=topo_2, db_path=db_path)

    assert sub_1 is not None
    assert sub_2 is not None


def test_quase_duplicata_escopada_por_nivel_nao_avisa_entre_pais_diferentes(db_path):
    """research.md #19: quase-duplicata so compara dentro do mesmo nivel
    -- subcategorias de pais diferentes com nomes parecidos nao geram
    aviso entre si."""
    topo_1 = storage_db.criar_categoria("Alimentação", db_path=db_path)
    topo_2 = storage_db.criar_categoria("Limpeza doméstica", db_path=db_path)
    storage_db.criar_categoria("Mercearia Seca", parent_id=topo_1, db_path=db_path)

    categoria_id, erro, aviso = categorias_service.validar_e_criar_categoria(
        "Mercearia", parent_id=topo_2, db_path=db_path
    )

    assert erro is None
    assert aviso is None
    assert isinstance(categoria_id, int)


def test_quase_duplicata_mesmo_nivel_gera_aviso_com_sugestao(db_path):
    original_id = storage_db.criar_categoria("Mercearia Seca", db_path=db_path)

    categoria_id, erro, aviso = categorias_service.validar_e_criar_categoria("Mercearia", db_path=db_path)

    assert categoria_id is None
    assert erro is None
    assert aviso["sugestao"]["id"] == original_id


def test_quase_duplicata_com_forcar_cria_mesmo_assim(db_path):
    storage_db.criar_categoria("Mercearia Seca", db_path=db_path)

    categoria_id, erro, aviso = categorias_service.validar_e_criar_categoria(
        "Mercearia", forcar=True, db_path=db_path
    )

    assert erro is None
    assert aviso is None
    assert isinstance(categoria_id, int)


def test_validar_e_criar_categoria_parent_id_de_subcategoria_retorna_erro(db_path):
    topo_id = storage_db.criar_categoria("Alimentação", db_path=db_path)
    sub_id = storage_db.criar_categoria("Mercearia seca", parent_id=topo_id, db_path=db_path)

    categoria_id, erro, aviso = categorias_service.validar_e_criar_categoria(
        "Nível 3", parent_id=sub_id, db_path=db_path
    )

    assert categoria_id is None
    assert erro == "Categoria pai não pode ser uma subcategoria."
    assert aviso is None


# --- US5 (T047/T048/T052): previa e exclusao com destino ------------------


def test_calcular_impacto_exclusao_categoria_inexistente_retorna_none(db_path):
    resultado = storage_db.calcular_impacto_exclusao(999, db_path=db_path)
    assert resultado is None


def test_calcular_impacto_exclusao_com_subcategorias(db_path):
    topo_id = storage_db.criar_categoria("Alimentação", db_path=db_path)
    storage_db.criar_categoria("Mercearia seca", parent_id=topo_id, db_path=db_path)

    impacto = storage_db.calcular_impacto_exclusao(topo_id, db_path=db_path)

    assert impacto["tem_subcategorias"] is True


def test_excluir_categoria_com_destino_bloqueada_por_subcategoria(db_path):
    topo_id = storage_db.criar_categoria("Alimentação", db_path=db_path)
    storage_db.criar_categoria("Mercearia seca", parent_id=topo_id, db_path=db_path)

    resultado = storage_db.excluir_categoria_com_destino(topo_id, "pendente", db_path=db_path)

    assert resultado is False
    assert storage_db.buscar_categoria_por_id(topo_id, db_path=db_path) is not None


def test_excluir_categoria_com_destino_substituta_reatribui_item_cache_regra(db_path):
    categoria_antiga = storage_db.criar_categoria("Categoria Antiga", db_path=db_path)
    categoria_nova = storage_db.criar_categoria("Categoria Nova", db_path=db_path)
    nota_id = _inserir_nota(db_path)
    item_id = _inserir_item(nota_id, "Item Teste", db_path=db_path)
    conn = storage_db.get_connection(db_path)
    conn.execute("UPDATE item_nota SET descricao_normalizada = 'ITEM TESTE' WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    storage_db.atribuir_categoria_manual(item_id, categoria_antiga, db_path=db_path)

    conn = storage_db.get_connection(db_path)
    conn.execute(
        "INSERT INTO regra_categoria (padrao, categoria_id, prioridade, ativa) VALUES (?, ?, 5, 1)",
        ("TESTE", categoria_antiga),
    )
    conn.commit()
    conn.close()

    resultado = storage_db.excluir_categoria_com_destino(
        categoria_antiga, "substituta", categoria_nova, db_path=db_path
    )

    assert resultado is True
    assert storage_db.buscar_categoria_por_id(categoria_antiga, db_path=db_path) is None

    item = storage_db.listar_itens_por_nota(nota_id, db_path=db_path)[0]
    assert item.categoria_id == categoria_nova

    conn = storage_db.get_connection(db_path)
    cache_row = conn.execute(
        "SELECT categoria_id FROM cache_descricao_categoria WHERE descricao_normalizada = ?", ("ITEM TESTE",)
    ).fetchone()
    regra_row = conn.execute("SELECT categoria_id FROM regra_categoria WHERE padrao = ?", ("TESTE",)).fetchone()
    conn.close()
    assert cache_row["categoria_id"] == categoria_nova
    assert regra_row["categoria_id"] == categoria_nova


def test_excluir_categoria_com_destino_substituta_nivel_diferente_retorna_false(db_path):
    topo_id = storage_db.criar_categoria("Alimentação", db_path=db_path)
    sub_id = storage_db.criar_categoria("Mercearia seca", parent_id=topo_id, db_path=db_path)
    outro_topo_id = storage_db.criar_categoria("Bebidas", db_path=db_path)

    resultado = storage_db.excluir_categoria_com_destino(sub_id, "substituta", outro_topo_id, db_path=db_path)

    assert resultado is False
    assert storage_db.buscar_categoria_por_id(sub_id, db_path=db_path) is not None


def test_excluir_categoria_com_destino_pendente_zera_item_e_remove_cache_regra(db_path):
    categoria_id = storage_db.criar_categoria("Categoria X", db_path=db_path)
    conn = storage_db.get_connection(db_path)
    conn.execute(
        "INSERT INTO cache_descricao_categoria (descricao_normalizada, categoria_id) VALUES (?, ?)",
        ("ITEM TESTE", categoria_id),
    )
    conn.commit()
    conn.close()

    resultado = storage_db.excluir_categoria_com_destino(categoria_id, "pendente", db_path=db_path)

    assert resultado is True
    conn = storage_db.get_connection(db_path)
    cache_row = conn.execute(
        "SELECT 1 FROM cache_descricao_categoria WHERE descricao_normalizada = ?", ("ITEM TESTE",)
    ).fetchone()
    conn.close()
    assert cache_row is None


def _inserir_transacao_com_categoria(db_path, categoria_id, fingerprint="fp-cat-teste") -> int:
    from src.models.transacao import Transacao, TipoTransacao

    transacao = Transacao(
        fingerprint=fingerprint,
        data="2026-06-01",
        descricao="Transacao Teste",
        valor=1000,
        tipo=TipoTransacao.SAIDA,
        conta="itau_2486",
        natureza="gasto",
        metodo_classificacao_natureza="regra",
        categoria_id=categoria_id,
    )
    return storage_db.inserir_transacao(transacao, db_path=db_path)


# --- feature 010: exclusao de categoria tambem afeta transacao/ -----------
# --- estabelecimento/cache-regra de natureza (regressao real no Pi dev) ---


def test_calcular_impacto_exclusao_inclui_referencias_da_feature_010(db_path):
    categoria_id = storage_db.criar_categoria("Contas de consumo", db_path=db_path)
    transacao_id = _inserir_transacao_com_categoria(db_path, categoria_id)
    estabelecimento_id = storage_db.obter_ou_criar_estabelecimento_por_descricao("LOJA TESTE", db_path=db_path)
    storage_db.atribuir_estabelecimento(estabelecimento_id, "Loja Teste", categoria_id, db_path=db_path)
    conn = storage_db.get_connection(db_path)
    conn.execute(
        "INSERT INTO regra_natureza (padrao, natureza, categoria_id, prioridade, ativa) VALUES ('TESTE', 'gasto', ?, 5, 1)",
        (categoria_id,),
    )
    conn.execute(
        "INSERT INTO cache_descricao_natureza (descricao_normalizada, natureza, categoria_id) VALUES ('TESTE', 'gasto', ?)",
        (categoria_id,),
    )
    conn.commit()
    conn.close()

    impacto = storage_db.calcular_impacto_exclusao(categoria_id, db_path=db_path)

    assert impacto["quantidade_transacoes"] == 1
    assert impacto["quantidade_estabelecimentos"] == 1
    assert impacto["quantidade_regras_natureza"] == 1
    assert impacto["quantidade_cache_natureza"] == 1


def test_excluir_categoria_com_destino_pendente_nao_quebra_com_transacao_vinculada(db_path):
    """Regressao real: excluir uma categoria referenciada so por
    transacao/estabelecimento/regra_natureza (sem nenhum item/nota) dava
    sqlite3.IntegrityError (FOREIGN KEY constraint failed) antes desta
    correcao, porque excluir_categoria_com_destino nao conhecia essas
    tabelas novas da feature 010."""
    categoria_id = storage_db.criar_categoria("Contas de consumo", db_path=db_path)
    transacao_id = _inserir_transacao_com_categoria(db_path, categoria_id)
    estabelecimento_id = storage_db.obter_ou_criar_estabelecimento_por_descricao("LOJA TESTE", db_path=db_path)
    storage_db.atribuir_estabelecimento(estabelecimento_id, "Loja Teste", categoria_id, db_path=db_path)
    conn = storage_db.get_connection(db_path)
    conn.execute(
        "INSERT INTO regra_natureza (padrao, natureza, categoria_id, prioridade, ativa) VALUES ('TESTE', 'gasto', ?, 5, 1)",
        (categoria_id,),
    )
    conn.execute(
        "INSERT INTO cache_descricao_natureza (descricao_normalizada, natureza, categoria_id) VALUES ('TESTE', 'gasto', ?)",
        (categoria_id,),
    )
    conn.commit()
    conn.close()

    resultado = storage_db.excluir_categoria_com_destino(categoria_id, "pendente", db_path=db_path)

    assert resultado is True
    assert storage_db.buscar_categoria_por_id(categoria_id, db_path=db_path) is None

    transacao = storage_db.buscar_transacao_por_id(transacao_id, db_path=db_path)
    assert transacao.categoria_id is None
    assert transacao.natureza == "gasto"  # natureza continua sabida -- so a categoria some
    assert transacao.metodo_classificacao_natureza == "regra"  # metodo da NATUREZA preservado

    estabelecimento = storage_db.buscar_estabelecimento_por_id(estabelecimento_id, db_path=db_path)
    assert estabelecimento.tipo_categoria_id is None

    conn = storage_db.get_connection(db_path)
    assert conn.execute("SELECT 1 FROM regra_natureza WHERE padrao = 'TESTE'").fetchone() is None
    assert conn.execute("SELECT 1 FROM cache_descricao_natureza WHERE descricao_normalizada = 'TESTE'").fetchone() is None
    conn.close()


def test_excluir_categoria_com_destino_substituta_reatribui_transacao_e_estabelecimento(db_path):
    categoria_antiga = storage_db.criar_categoria("Categoria Antiga", db_path=db_path)
    categoria_nova = storage_db.criar_categoria("Categoria Nova", db_path=db_path)
    transacao_id = _inserir_transacao_com_categoria(db_path, categoria_antiga)
    estabelecimento_id = storage_db.obter_ou_criar_estabelecimento_por_descricao("LOJA TESTE", db_path=db_path)
    storage_db.atribuir_estabelecimento(estabelecimento_id, "Loja Teste", categoria_antiga, db_path=db_path)

    resultado = storage_db.excluir_categoria_com_destino(
        categoria_antiga, "substituta", categoria_nova, db_path=db_path
    )

    assert resultado is True
    transacao = storage_db.buscar_transacao_por_id(transacao_id, db_path=db_path)
    assert transacao.categoria_id == categoria_nova
    estabelecimento = storage_db.buscar_estabelecimento_por_id(estabelecimento_id, db_path=db_path)
    assert estabelecimento.tipo_categoria_id == categoria_nova


def test_editar_categoria_preserva_parent_id_e_nao_gera_historico(db_path):
    """FR-003: renomear uma categoria/subcategoria nao afeta parent_id nem
    gera nenhuma linha em historico_classificacao_item -- e uma operacao
    de metadado, nao de reclassificacao de item."""
    topo_id = storage_db.criar_categoria("Alimentação", db_path=db_path)
    sub_id = storage_db.criar_categoria("Mercearia seca", parent_id=topo_id, db_path=db_path)

    storage_db.editar_categoria(sub_id, "Mercearia Seca Renomeada", db_path=db_path)

    categoria = storage_db.buscar_categoria_por_id(sub_id, db_path=db_path)
    assert categoria.nome == "Mercearia Seca Renomeada"
    assert categoria.parent_id == topo_id

    conn = storage_db.get_connection(db_path)
    total_historico = conn.execute("SELECT COUNT(*) FROM historico_classificacao_item").fetchone()[0]
    conn.close()
    assert total_historico == 0
