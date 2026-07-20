from __future__ import annotations

import pytest

from src.models.nota_fiscal import CanalOrigem, NotaFiscal, StatusNota
from src.models.transacao import Transacao, TipoTransacao
from src.services import estabelecimento as estabelecimento_service
from src.storage import db as storage_db
from tests.helpers import gerar_chave_valida


@pytest.fixture()
def db_path(tmp_path):
    caminho = str(tmp_path / "financiall.db")
    storage_db.init_db(caminho)
    return caminho


def _inserir_transacao(db_path, descricao, descricao_normalizada=None, nota_fiscal_id=None, fingerprint=None) -> int:
    transacao = Transacao(
        fingerprint=fingerprint or f"fp-{descricao}",
        data="2026-06-10",
        descricao=descricao,
        descricao_normalizada=descricao_normalizada or descricao.upper(),
        valor=1000,
        tipo=TipoTransacao.SAIDA,
        conta="itau_2486",
        natureza="gasto",
        nota_fiscal_id=nota_fiscal_id,
    )
    return storage_db.inserir_transacao(transacao, db_path=db_path)


# --- extrair_documento -------------------------------------------------


@pytest.mark.parametrize(
    "descricao,esperado",
    [
        ("PIX RECEBIDO DE JOAO 123.456.789-01", "12345678901"),
        ("PIX QRS EMPRESA X 12.345.678/0001-99", "12345678000199"),
        ("PIX SEM DOCUMENTO NENHUM", None),
        ("TBI 0300.46235-5", None),  # numero de conta, nao e CPF/CNPJ
        (None, None),
    ],
)
def test_extrair_documento(descricao, esperado):
    assert estabelecimento_service.extrair_documento(descricao) == esperado


# --- resolver_estabelecimento: cascata ----------------------------------


def test_resolver_estabelecimento_transacao_inexistente_retorna_none(db_path):
    resultado = estabelecimento_service.resolver_estabelecimento(999, db_path=db_path)
    assert resultado is None


def test_resolver_estabelecimento_via_cnpj_da_nota_reconciliada(db_path):
    nota = NotaFiscal(
        canal_origem=CanalOrigem.URL_CHAVE,
        status=StatusNota.COMPLETA,
        chave_acesso=gerar_chave_valida(numero="000000001"),
        cnpj_emitente="11222333000144",
    )
    nota_id = storage_db.inserir_nota(nota, db_path=db_path)
    transacao_id = _inserir_transacao(db_path, "SJX COMERCIAL", nota_fiscal_id=nota_id)

    estabelecimento_id = estabelecimento_service.resolver_estabelecimento(transacao_id, db_path=db_path)

    estabelecimento = storage_db.buscar_estabelecimento_por_id(estabelecimento_id, db_path=db_path)
    assert estabelecimento.documento == "11222333000144"


def test_resolver_estabelecimento_via_documento_na_propria_descricao(db_path):
    transacao_id = _inserir_transacao(db_path, "PIX RECEBIDO 123.456.789-01")

    estabelecimento_id = estabelecimento_service.resolver_estabelecimento(transacao_id, db_path=db_path)

    estabelecimento = storage_db.buscar_estabelecimento_por_id(estabelecimento_id, db_path=db_path)
    assert estabelecimento.documento == "12345678901"


def test_resolver_estabelecimento_fallback_por_descricao_normalizada(db_path):
    transacao_id = _inserir_transacao(db_path, "SJX Comercial Ltda", descricao_normalizada="SJX COMERCIAL LTDA")

    estabelecimento_id = estabelecimento_service.resolver_estabelecimento(transacao_id, db_path=db_path)

    estabelecimento = storage_db.buscar_estabelecimento_por_id(estabelecimento_id, db_path=db_path)
    assert estabelecimento.documento is None
    assert estabelecimento.descricao_normalizada == "SJX COMERCIAL LTDA"


def test_resolver_estabelecimento_duas_transacoes_mesma_descricao_compartilham_estabelecimento(db_path):
    t1 = _inserir_transacao(db_path, "SJX Comercial", descricao_normalizada="SJX COMERCIAL", fingerprint="fp-1")
    t2 = _inserir_transacao(db_path, "SJX Comercial", descricao_normalizada="SJX COMERCIAL", fingerprint="fp-2")

    id_1 = estabelecimento_service.resolver_estabelecimento(t1, db_path=db_path)
    id_2 = estabelecimento_service.resolver_estabelecimento(t2, db_path=db_path)

    assert id_1 == id_2


# --- FR-019: promocao/fusao quando descricao ganha documento depois -----


def test_resolver_estabelecimento_promove_de_descricao_para_documento(db_path):
    """Transacao resolvida por descricao primeiro; depois reconcilia com
    nota que traz CNPJ -- deve promover pro documento, sem criar uma
    segunda identidade (FR-019)."""
    transacao_id = _inserir_transacao(db_path, "SJX Comercial", descricao_normalizada="SJX COMERCIAL")
    id_por_descricao = estabelecimento_service.resolver_estabelecimento(transacao_id, db_path=db_path)
    assert storage_db.buscar_estabelecimento_por_id(id_por_descricao, db_path=db_path).documento is None

    nota = NotaFiscal(
        canal_origem=CanalOrigem.URL_CHAVE,
        status=StatusNota.COMPLETA,
        chave_acesso=gerar_chave_valida(numero="000000002"),
        cnpj_emitente="99888777000166",
    )
    nota_id = storage_db.inserir_nota(nota, db_path=db_path)
    storage_db.vincular_reconciliacao_manual(transacao_id, nota_id, db_path=db_path)

    id_por_documento = estabelecimento_service.resolver_estabelecimento(transacao_id, db_path=db_path)

    assert storage_db.buscar_estabelecimento_por_id(id_por_documento, db_path=db_path).documento == "99888777000166"
    # a identidade antiga (por descricao) nao sobrevive como registro solto
    assert storage_db.buscar_estabelecimento_por_id(id_por_descricao, db_path=db_path) is None or id_por_descricao == id_por_documento


def test_resolver_estabelecimento_funde_com_estabelecimento_ja_existente_por_documento(db_path):
    """Se ja existe um estabelecimento pelo mesmo documento (de outra
    transacao), a promocao funde nele em vez de manter dois."""
    nota = NotaFiscal(
        canal_origem=CanalOrigem.URL_CHAVE,
        status=StatusNota.COMPLETA,
        chave_acesso=gerar_chave_valida(numero="000000003"),
        cnpj_emitente="55444333000122",
    )
    nota_id = storage_db.inserir_nota(nota, db_path=db_path)
    transacao_com_cnpj = _inserir_transacao(db_path, "Loja Y", nota_fiscal_id=nota_id, fingerprint="fp-cnpj")
    id_existente_por_documento = estabelecimento_service.resolver_estabelecimento(transacao_com_cnpj, db_path=db_path)

    transacao_por_descricao = _inserir_transacao(
        db_path, "Loja Y Descricao", descricao_normalizada="LOJA Y DESCRICAO", fingerprint="fp-desc"
    )
    id_por_descricao = estabelecimento_service.resolver_estabelecimento(transacao_por_descricao, db_path=db_path)
    assert id_por_descricao != id_existente_por_documento

    storage_db.vincular_transacao_a_estabelecimento(transacao_por_descricao, id_por_descricao, db_path=db_path)
    id_fundido = storage_db.promover_estabelecimento_para_documento(
        id_por_descricao, "55444333000122", db_path=db_path
    )

    assert id_fundido == id_existente_por_documento
    transacao_atualizada = storage_db.buscar_transacao_por_id(transacao_por_descricao, db_path=db_path)
    assert transacao_atualizada.estabelecimento_id == id_existente_por_documento


# --- bug real: grafias truncadas diferentes duplicavam a sugestao de nome --


def test_atribuir_estabelecimento_mesmo_nome_funde_em_vez_de_duplicar(db_path):
    """Bug relatado pelo usuario: classificar duas descricoes truncadas
    diferentes ('LETICIA ARTE-CT ENTO', 'LETICIA ARTE TALENTO') com o
    mesmo nome fantasia criava duas linhas de Estabelecimento, e a
    sugestao de nomes ja usados aparecia duplicada. atribuir_estabelecimento
    agora funde na existente em vez de manter duas identidades."""
    tipo_id = storage_db.criar_categoria("Padaria", db_path=db_path)
    t1 = _inserir_transacao(db_path, "Leticia Arte Talento", descricao_normalizada="LETICIA ARTE TALENTO", fingerprint="fp-lt1")
    est1_id = estabelecimento_service.resolver_estabelecimento(t1, db_path=db_path)
    storage_db.atribuir_estabelecimento(est1_id, "Letícia Arte e Talento", tipo_id, db_path=db_path)

    t2 = _inserir_transacao(db_path, "Leticia Arte-ct Ento", descricao_normalizada="LETICIA ARTE-CT ENTO", fingerprint="fp-lt2")
    est2_id = estabelecimento_service.resolver_estabelecimento(t2, db_path=db_path)
    resultado = storage_db.atribuir_estabelecimento(est2_id, "Letícia Arte e Talento", None, db_path=db_path)

    assert resultado is True
    # a segunda linha foi fundida na primeira, nao criou uma terceira identidade
    assert storage_db.buscar_estabelecimento_por_id(est2_id, db_path=db_path) is None
    transacao_2_atualizada = storage_db.buscar_transacao_por_id(t2, db_path=db_path)
    assert transacao_2_atualizada.estabelecimento_id == est1_id

    nomeados = storage_db.listar_estabelecimentos_nomeados(db_path=db_path)
    assert len(nomeados) == 1
    assert nomeados[0]["tipo_categoria_id"] == tipo_id


def test_listar_estabelecimentos_nomeados_deduplica_por_nome_registros_antigos(db_path):
    """Cobre o caso de dado ja duplicado ANTES desta correcao existir
    (registros legados) -- a listagem de sugestao nunca deve repetir o
    mesmo nome, mesmo que existam duas linhas reais no banco."""
    tipo_id = storage_db.criar_categoria("Padaria", db_path=db_path)
    t1 = _inserir_transacao(db_path, "Loja A", descricao_normalizada="LOJA A", fingerprint="fp-dup1")
    est1_id = estabelecimento_service.resolver_estabelecimento(t1, db_path=db_path)
    t2 = _inserir_transacao(db_path, "Loja A Variante", descricao_normalizada="LOJA A VARIANTE", fingerprint="fp-dup2")
    est2_id = estabelecimento_service.resolver_estabelecimento(t2, db_path=db_path)

    # simula o estado legado: duas linhas com o MESMO nome (antes do merge existir)
    conn = storage_db.get_connection(db_path)
    conn.execute("UPDATE estabelecimento SET nome_fantasia = ?, tipo_categoria_id = ? WHERE id = ?", ("Loja A", tipo_id, est1_id))
    conn.execute("UPDATE estabelecimento SET nome_fantasia = ?, tipo_categoria_id = ? WHERE id = ?", ("Loja A", tipo_id, est2_id))
    conn.commit()
    conn.close()

    nomeados = storage_db.listar_estabelecimentos_nomeados(db_path=db_path)

    assert len(nomeados) == 1
    assert nomeados[0]["nome_fantasia"] == "Loja A"


# --- bug real: transacao reconciliada com nota criava CNPJ separado do ----
# --- estabelecimento ja resolvido por descricao para o mesmo lugar --------


def test_resolver_estabelecimento_cnpj_da_nota_e_normalizado(db_path):
    """nota_fiscal.cnpj_emitente vem formatado (##.###.###/####-##) --
    resolver_estabelecimento precisa normalizar pra so digitos, senao o
    mesmo CNPJ vindo por essa via e pela via de PIX (ja so digitos) nunca
    bateriam."""
    nota = NotaFiscal(
        canal_origem=CanalOrigem.URL_CHAVE,
        status=StatusNota.COMPLETA,
        chave_acesso=gerar_chave_valida(numero="000000004"),
        cnpj_emitente="17.608.063/0005-51",
    )
    nota_id = storage_db.inserir_nota(nota, db_path=db_path)
    transacao_id = _inserir_transacao(db_path, "SJX Comercial", nota_fiscal_id=nota_id)

    estabelecimento_id = estabelecimento_service.resolver_estabelecimento(transacao_id, db_path=db_path)

    estabelecimento = storage_db.buscar_estabelecimento_por_id(estabelecimento_id, db_path=db_path)
    assert estabelecimento.documento == "17608063000551"


def test_resolver_estabelecimento_promove_match_exato_por_descricao_ao_inves_de_duplicar(db_path):
    """Bug real: uma transacao SEM nota resolve 'SJX - COMERCIAL ATACAD'
    por descricao; depois, OUTRA transacao com a mesma descricao exata
    reconcilia com uma nota que traz CNPJ -- em vez de criar um segundo
    estabelecimento (documento), deve promover o ja existente por
    descricao pro documento."""
    t1 = _inserir_transacao(
        db_path, "SJX - Comercial Atacad", descricao_normalizada="SJX - COMERCIAL ATACAD", fingerprint="fp-desc-primeiro"
    )
    id_por_descricao = estabelecimento_service.resolver_estabelecimento(t1, db_path=db_path)
    assert storage_db.buscar_estabelecimento_por_id(id_por_descricao, db_path=db_path).documento is None

    nota = NotaFiscal(
        canal_origem=CanalOrigem.URL_CHAVE,
        status=StatusNota.COMPLETA,
        chave_acesso=gerar_chave_valida(numero="000000005"),
        cnpj_emitente="17.608.063/0005-51",
    )
    nota_id = storage_db.inserir_nota(nota, db_path=db_path)
    t2 = _inserir_transacao(
        db_path,
        "SJX - Comercial Atacad",
        descricao_normalizada="SJX - COMERCIAL ATACAD",
        nota_fiscal_id=nota_id,
        fingerprint="fp-desc-segundo",
    )

    id_promovido = estabelecimento_service.resolver_estabelecimento(t2, db_path=db_path)

    assert id_promovido == id_por_descricao
    estabelecimento = storage_db.buscar_estabelecimento_por_id(id_promovido, db_path=db_path)
    assert estabelecimento.documento == "17608063000551"
    # a primeira transacao tambem enxerga o mesmo estabelecimento promovido
    transacao_1_atual = storage_db.buscar_transacao_por_id(t1, db_path=db_path)
    assert transacao_1_atual.estabelecimento_id == id_promovido


# --- exemplo de descricao na fila de pendentes (recognoscibilidade) -------


def test_listar_estabelecimentos_pendentes_inclui_exemplo_descricao(db_path):
    transacao_id = _inserir_transacao(db_path, "SJX - Comercial Atacad Sao Paulo Bra")
    estabelecimento_service.resolver_estabelecimento(transacao_id, db_path=db_path)

    pendentes = storage_db.listar_estabelecimentos_pendentes(db_path=db_path)

    assert len(pendentes) == 1
    assert pendentes[0]["exemplo_descricao"] == "SJX - Comercial Atacad Sao Paulo Bra"
