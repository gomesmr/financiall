from __future__ import annotations

import pytest

from src.models.item_nota import ItemNota
from src.models.nota_fiscal import CanalOrigem, NotaFiscal, StatusNota
from src.services import exclusao
from src.storage import db as storage_db
from tests.helpers import gerar_chave_valida


@pytest.fixture()
def db_path(tmp_path):
    caminho = str(tmp_path / "financiall.db")
    storage_db.init_db(caminho)
    return caminho


def _inserir_nota_com_item(db_path, status: StatusNota = StatusNota.COMPLETA) -> int:
    nota = NotaFiscal(
        canal_origem=CanalOrigem.URL_CHAVE,
        status=status,
        chave_acesso=gerar_chave_valida(),
    )
    nota_id = storage_db.inserir_nota(nota, db_path=db_path)
    storage_db.inserir_itens(
        [ItemNota(nota_fiscal_id=nota_id, descricao="Item de teste", valor_total_item=1000)],
        db_path=db_path,
    )
    return nota_id


def _inserir_envio_vinculado(db_path, nota_id: int, tmp_path, nome: str = "foto.jpg"):
    caminho = tmp_path / nome
    caminho.write_bytes(b"conteudo de teste")
    envio_id = storage_db.inserir_envio(str(caminho), "foto", "hash-qualquer", db_path=db_path)
    storage_db.atualizar_status_envio(envio_id, "concluido", nota_fiscal_id=nota_id, db_path=db_path)
    return envio_id, caminho


# --- US1: excluir nota, itens, envios e arquivos ------------------------


def test_excluir_nota_remove_nota_e_itens(db_path):
    nota_id = _inserir_nota_com_item(db_path)

    resultado = exclusao.excluir_nota_fiscal(nota_id, db_path=db_path)

    assert resultado is True
    assert storage_db.buscar_nota_por_id(nota_id, db_path=db_path) is None
    assert storage_db.listar_itens_por_nota(nota_id, db_path=db_path) == []


def test_excluir_nota_remove_envio_e_arquivo_associados(db_path, tmp_path):
    nota_id = _inserir_nota_com_item(db_path)
    envio_id, caminho = _inserir_envio_vinculado(db_path, nota_id, tmp_path)
    assert caminho.exists()

    exclusao.excluir_nota_fiscal(nota_id, db_path=db_path)

    assert storage_db.buscar_envio_por_id(envio_id, db_path=db_path) is None
    assert not caminho.exists()


def test_excluir_nota_com_multiplos_envios_remove_todos_os_arquivos(db_path, tmp_path):
    nota_id = _inserir_nota_com_item(db_path)
    envio_1, caminho_1 = _inserir_envio_vinculado(db_path, nota_id, tmp_path, "foto1.jpg")
    envio_2, caminho_2 = _inserir_envio_vinculado(db_path, nota_id, tmp_path, "foto2.jpg")

    exclusao.excluir_nota_fiscal(nota_id, db_path=db_path)

    assert storage_db.buscar_envio_por_id(envio_1, db_path=db_path) is None
    assert storage_db.buscar_envio_por_id(envio_2, db_path=db_path) is None
    assert not caminho_1.exists()
    assert not caminho_2.exists()


def test_excluir_nota_pendente_revisao_funciona_igual_a_completa(db_path):
    nota_id = _inserir_nota_com_item(db_path, status=StatusNota.PENDENTE_REVISAO)

    resultado = exclusao.excluir_nota_fiscal(nota_id, db_path=db_path)

    assert resultado is True
    assert storage_db.buscar_nota_por_id(nota_id, db_path=db_path) is None


def test_excluir_nota_com_arquivo_ja_ausente_nao_levanta_excecao(db_path, tmp_path):
    nota_id = _inserir_nota_com_item(db_path)
    _, caminho = _inserir_envio_vinculado(db_path, nota_id, tmp_path)
    caminho.unlink()  # simula arquivo ja removido por fora do sistema (research.md #2)

    resultado = exclusao.excluir_nota_fiscal(nota_id, db_path=db_path)

    assert resultado is True
    assert storage_db.buscar_nota_por_id(nota_id, db_path=db_path) is None


# --- US3: nota inexistente -----------------------------------------------


def test_excluir_nota_inexistente_retorna_false_sem_excecao(db_path):
    resultado = exclusao.excluir_nota_fiscal(999, db_path=db_path)
    assert resultado is False
