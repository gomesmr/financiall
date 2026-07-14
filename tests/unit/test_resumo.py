from __future__ import annotations

from datetime import date

import pytest

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
