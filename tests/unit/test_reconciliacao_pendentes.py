from __future__ import annotations

import pytest

from src.models.nota_fiscal import CanalOrigem, NotaFiscal, StatusNota
from src.models.transacao import Transacao, TipoTransacao
from src.services import reconciliacao
from src.services.importar_historico_extrato import processar_transacoes
from src.storage import db as storage_db
from tests.helpers import gerar_chave_valida

_contador_notas = 0


@pytest.fixture()
def db_path(tmp_path):
    caminho = str(tmp_path / "financiall.db")
    storage_db.init_db(caminho)
    return caminho


def _inserir_nota(valor_total: int, data_emissao: str, db_path, categoria_id: int | None = None) -> int:
    global _contador_notas
    _contador_notas += 1
    nota = NotaFiscal(
        canal_origem=CanalOrigem.URL_CHAVE,
        status=StatusNota.COMPLETA,
        chave_acesso=gerar_chave_valida(numero=str(_contador_notas).zfill(9)),
        valor_total=valor_total,
        data_emissao=data_emissao,
    )
    nota_id = storage_db.inserir_nota(nota, db_path=db_path)
    if categoria_id is not None:
        conn = storage_db.get_connection(db_path)
        conn.execute("UPDATE nota_fiscal SET categoria_id = ? WHERE id = ?", (categoria_id, nota_id))
        conn.commit()
        conn.close()
    return nota_id


def _criar_categoria(nome: str, db_path) -> int:
    conn = storage_db.get_connection(db_path)
    cursor = conn.execute(
        "INSERT INTO categoria (nome, nome_normalizado) VALUES (?, ?)", (nome, nome.strip().casefold())
    )
    conn.commit()
    conn.close()
    return cursor.lastrowid


def _registro(data: str, descricao: str, valor_raw: float, conta: str = "Itaú_CC"):
    return {"data": data, "descricao": descricao, "valor_raw": valor_raw, "conta": conta, "fonte": "extrato.json"}


# --- importacao ------------------------------------------------------------


def test_saida_pendente_que_bate_com_nota_vira_gasto_com_categoria_da_nota(db_path):
    categoria_id = _criar_categoria("Mercado Teste", db_path)
    nota_id = _inserir_nota(18740, "2026-09-22", db_path, categoria_id=categoria_id)

    resumo = processar_transacoes(
        [_registro("2026-09-22", "Compra débito MERCADINHO SEM REGRA", -187.40)], db_path=db_path
    )

    assert resumo.reconciliadas == 1
    assert resumo.pendentes_natureza == 0
    assert resumo.classificadas_automaticamente == 1
    conn = storage_db.get_connection(db_path)
    row = conn.execute("SELECT natureza, categoria_id, nota_fiscal_id FROM transacao").fetchone()
    conn.close()
    assert row["natureza"] == "gasto"
    assert row["categoria_id"] == categoria_id
    assert row["nota_fiscal_id"] == nota_id


def test_saida_pendente_sem_nota_continua_pendente(db_path):
    resumo = processar_transacoes(
        [_registro("2026-09-22", "Compra débito MERCADINHO SEM REGRA", -187.40)], db_path=db_path
    )

    assert resumo.reconciliadas == 0
    assert resumo.pendentes_natureza == 1


def test_entrada_pendente_nunca_reconcilia_com_nota(db_path):
    _inserir_nota(20000, "2026-09-22", db_path)

    resumo = processar_transacoes([_registro("2026-09-22", "PIX RECEBIDO FULANO", 200.00)], db_path=db_path)

    assert resumo.reconciliadas == 0
    assert resumo.pendentes_natureza == 1


# --- depois de classificacao manual ---------------------------------------


def _inserir_transacao(natureza: str | None, valor: int = 9990, data: str = "2026-09-09") -> Transacao:
    return Transacao(
        fingerprint=f"fp-{valor}-{data}",
        data=data,
        descricao="Compra débito MERCADINHO",
        descricao_normalizada="COMPRA DEBITO MERCADINHO",
        valor=valor,
        tipo=TipoTransacao.SAIDA,
        conta="itau_cc",
        natureza=natureza,
    )


def test_reconciliar_gastos_sem_nota_liga_gasto_classificado_depois(db_path):
    nota_id = _inserir_nota(9990, "2026-09-07", db_path)
    transacao_id = storage_db.inserir_transacao(_inserir_transacao("gasto"), db_path=db_path)

    reconciliadas = reconciliacao.reconciliar_gastos_sem_nota([transacao_id], db_path=db_path)

    assert reconciliadas == 1
    assert storage_db.buscar_transacao_por_id(transacao_id, db_path=db_path).nota_fiscal_id == nota_id


def test_reconciliar_gastos_sem_nota_ignora_o_que_nao_e_gasto(db_path):
    _inserir_nota(9990, "2026-09-07", db_path)
    transacao_id = storage_db.inserir_transacao(_inserir_transacao("transferencia_interna"), db_path=db_path)

    assert reconciliacao.reconciliar_gastos_sem_nota([transacao_id], db_path=db_path) == 0


def test_put_natureza_gasto_dispara_reconciliacao(client, app_e_db):
    _, db_path = app_e_db
    categoria_id = _criar_categoria("Mercado Teste", db_path)
    nota_id = _inserir_nota(9990, "2026-09-07", db_path)
    transacao_id = storage_db.inserir_transacao(_inserir_transacao(None), db_path=db_path)

    resposta = client.put(
        f"/transacoes/{transacao_id}/natureza", json={"natureza": "gasto", "categoria_id": categoria_id}
    )

    assert resposta.status_code == 200
    assert storage_db.buscar_transacao_por_id(transacao_id, db_path=db_path).nota_fiscal_id == nota_id


def test_classificar_grupo_como_gasto_dispara_reconciliacao(client, app_e_db):
    _, db_path = app_e_db
    categoria_id = _criar_categoria("Mercado Teste", db_path)
    nota_id = _inserir_nota(9990, "2026-09-07", db_path)
    transacao_id = storage_db.inserir_transacao(_inserir_transacao(None), db_path=db_path)

    resposta = client.post(
        "/transacoes/pendentes/classificar-grupo",
        json={"descricao_normalizada": "COMPRA DEBITO MERCADINHO", "natureza": "gasto", "categoria_id": categoria_id},
    )

    assert resposta.status_code == 200
    assert storage_db.buscar_transacao_por_id(transacao_id, db_path=db_path).nota_fiscal_id == nota_id
