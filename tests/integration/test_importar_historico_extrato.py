from __future__ import annotations

import json

import pytest

from src.scripts.seed_regras_natureza import seed_regras_natureza
from src.scripts.seed_taxonomia_categorizacao import seed_taxonomia
from src.services.importar_historico_extrato import ArquivoExtratoError, importar_historico_extrato
from src.storage import db as storage_db


@pytest.fixture()
def db_path(tmp_path):
    caminho = str(tmp_path / "financiall.db")
    storage_db.init_db(caminho)
    seed_taxonomia(db_path=caminho)
    seed_regras_natureza(db_path=caminho)
    return caminho


def _escrever_registro(tmp_path, conteudo: dict) -> str:
    caminho = tmp_path / "registro.json"
    caminho.write_text(json.dumps(conteudo, ensure_ascii=False), encoding="utf-8")
    return str(caminho)


_REGISTRO_SINTETICO = {
    "fp1": {"data": "2026-06-10", "desc": "SJX COMERCIAL LTDA", "valor": "150.00", "conta": "2486", "fonte": "f1"},
    "fp2": {"data": "2026-06-11", "desc": "SJX COMERCIAL LTDA", "valor": "80.00", "conta": "Itaú_2486", "fonte": "f2"},
    "fp3": {"data": "2026-06-12", "desc": "PAGTO SALARIO REF 06/2026", "valor": "5000.00", "conta": "Itaú_CC", "fonte": "f3"},
    "fp4": {"data": "2026-06-13", "desc": "FATURA PAGA", "valor": "-230.00", "conta": "Itaú_CC", "fonte": "f4"},
    "fp5": {"data": "2026-06-14", "desc": "Depósito", "valor": "300.00", "conta": "Flash", "fonte": "f5"},
    "fp6": {"data": "2026-06-15", "desc": "RESTAURANTE QUALQUER", "valor": "45.00", "conta": "Flash", "fonte": "f6"},
    "fp7_malformado": {"desc": "SEM DATA NEM VALOR", "conta": "2486"},
}


def test_importar_historico_extrato_importa_todas_as_transacoes_validas(tmp_path, db_path):
    caminho = _escrever_registro(tmp_path, _REGISTRO_SINTETICO)

    resumo = importar_historico_extrato(caminho, db_path=db_path)

    assert resumo.importadas == 6
    assert resumo.puladas == 1
    assert resumo.ja_existentes == 0

    conn = storage_db.get_connection(db_path)
    total = conn.execute("SELECT COUNT(*) FROM transacao").fetchone()[0]
    conn.close()
    assert total == 6


def test_importar_historico_extrato_consolida_contas_duplicadas(tmp_path, db_path):
    caminho = _escrever_registro(tmp_path, _REGISTRO_SINTETICO)
    importar_historico_extrato(caminho, db_path=db_path)

    conn = storage_db.get_connection(db_path)
    contas = {row["conta"] for row in conn.execute("SELECT DISTINCT conta FROM transacao").fetchall()}
    conn.close()

    assert "2486" not in contas
    assert "Itaú_2486" not in contas
    assert "itau_2486" in contas


def test_importar_historico_extrato_e_idempotente(tmp_path, db_path):
    caminho = _escrever_registro(tmp_path, _REGISTRO_SINTETICO)
    primeira = importar_historico_extrato(caminho, db_path=db_path)

    segunda = importar_historico_extrato(caminho, db_path=db_path)

    assert segunda.importadas == 0
    assert segunda.ja_existentes == primeira.importadas


def test_importar_historico_extrato_classifica_natureza_automaticamente(tmp_path, db_path):
    caminho = _escrever_registro(tmp_path, _REGISTRO_SINTETICO)
    importar_historico_extrato(caminho, db_path=db_path)

    conn = storage_db.get_connection(db_path)
    naturezas = {row["descricao"]: row["natureza"] for row in conn.execute("SELECT descricao, natureza FROM transacao").fetchall()}
    conn.close()

    assert naturezas["PAGTO SALARIO REF 06/2026"] == "renda"
    assert naturezas["FATURA PAGA"] == "pagamento_fatura"
    assert naturezas["Depósito"] == "renda"
    assert naturezas["SJX COMERCIAL LTDA"] == "gasto"


def test_importar_historico_extrato_tipo_derivado_corretamente_por_conta(tmp_path, db_path):
    """Cartao: positivo=saida; conta corrente: negativo=saida,
    positivo=entrada; Flash: 'Deposito' = entrada, resto = saida."""
    caminho = _escrever_registro(tmp_path, _REGISTRO_SINTETICO)
    importar_historico_extrato(caminho, db_path=db_path)

    conn = storage_db.get_connection(db_path)
    tipos = {row["descricao"]: row["tipo"] for row in conn.execute("SELECT descricao, tipo FROM transacao").fetchall()}
    conn.close()

    assert tipos["SJX COMERCIAL LTDA"] == "saida"  # cartao, valor positivo
    assert tipos["PAGTO SALARIO REF 06/2026"] == "entrada"  # CC, valor positivo
    assert tipos["FATURA PAGA"] == "saida"  # CC, valor negativo
    assert tipos["Depósito"] == "entrada"  # Flash, descricao "Deposito"
    assert tipos["RESTAURANTE QUALQUER"] == "saida"  # Flash, descricao qualquer


def test_importar_historico_extrato_arquivo_ausente_levanta_erro(db_path):
    with pytest.raises(ArquivoExtratoError):
        importar_historico_extrato("/caminho/que/nao/existe.json", db_path=db_path)


def test_importar_historico_extrato_json_invalido_levanta_erro(tmp_path, db_path):
    caminho = tmp_path / "registro.json"
    caminho.write_text("{ isso nao e json valido", encoding="utf-8")

    with pytest.raises(ArquivoExtratoError):
        importar_historico_extrato(str(caminho), db_path=db_path)
