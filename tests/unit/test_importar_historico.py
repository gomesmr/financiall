from __future__ import annotations

import json

import pytest

from src.services.importar_historico import ArquivoHistoricoError, importar_historico
from src.storage import db as storage_db
from tests.helpers import gerar_chave_valida


@pytest.fixture()
def db_path(tmp_path):
    caminho = str(tmp_path / "financiall.db")
    storage_db.init_db(caminho)
    return caminho


def _escrever_arquivo(tmp_path, dados: dict) -> str:
    caminho = tmp_path / "historico.json"
    caminho.write_text(json.dumps(dados), encoding="utf-8")
    return str(caminho)


def _registro_sintetico(conta: str = "marcelo", fonte: str = "qr", **overrides) -> dict:
    registro = {
        "emitente": "Loja Exemplo Sintetica",
        "cnpj": "12.345.678/0001-99",
        "uf": "SP",
        "data_emissao": "22/02/2025",
        "total": 100.5,
        "itens": [
            {
                "descricao": "Item Exemplo",
                "codigo": "123",
                "qtd": 1.0,
                "un": "UN",
                "vl_unit": 100.5,
                "vl_total": 100.5,
                "desconto": 0,
                "vl_liquido": 100.5,
            }
        ],
        "importado_em": "2026-01-01 10:00",
        "conta": conta,
        "fonte": fonte,
    }
    registro.update(overrides)
    return registro


# --- US1: mapeamento e gravacao -------------------------------------------


def test_importar_historico_grava_nota_com_itens_convertidos(db_path, tmp_path):
    chave = gerar_chave_valida()
    arquivo = _escrever_arquivo(tmp_path, {chave: _registro_sintetico()})

    resumo = importar_historico(arquivo, db_path=db_path)

    assert resumo.importadas == 1
    assert resumo.ja_existentes == 0
    assert resumo.puladas == 0

    nota = storage_db.buscar_por_chave_acesso(chave, db_path=db_path)
    assert nota is not None
    assert nota.status.value == "completa"
    assert nota.canal_origem.value == "url_chave"
    assert nota.categoria_id is None
    assert nota.titular == "marcelo"
    assert nota.data_emissao == "2025-02-22"
    assert nota.ano_mes_emissao == "2502"
    assert nota.valor_total == 10050

    itens = storage_db.listar_itens_por_nota(nota.id, db_path=db_path)
    assert len(itens) == 1
    assert itens[0].valor_total_item == 10050


def test_importar_historico_prefere_vl_liquido_quando_ha_desconto(db_path, tmp_path):
    chave = gerar_chave_valida()
    registro = _registro_sintetico()
    registro["itens"][0]["vl_total"] = 100.0
    registro["itens"][0]["vl_liquido"] = 80.0
    arquivo = _escrever_arquivo(tmp_path, {chave: registro})

    importar_historico(arquivo, db_path=db_path)

    nota = storage_db.buscar_por_chave_acesso(chave, db_path=db_path)
    itens = storage_db.listar_itens_por_nota(nota.id, db_path=db_path)
    assert itens[0].valor_total_item == 8000


def test_importar_historico_fonte_pdf_mapeia_canal_foto_pdf(db_path, tmp_path):
    chave = gerar_chave_valida()
    arquivo = _escrever_arquivo(tmp_path, {chave: _registro_sintetico(fonte="pdf")})

    importar_historico(arquivo, db_path=db_path)

    nota = storage_db.buscar_por_chave_acesso(chave, db_path=db_path)
    assert nota.canal_origem.value == "foto_pdf"


def test_importar_historico_conta_desconhecida_vira_nao_identificado(db_path, tmp_path):
    chave = gerar_chave_valida()
    arquivo = _escrever_arquivo(tmp_path, {chave: _registro_sintetico(conta="outra_pessoa")})

    importar_historico(arquivo, db_path=db_path)

    nota = storage_db.buscar_por_chave_acesso(chave, db_path=db_path)
    assert nota.titular == "nao_identificado"


def test_importar_historico_nota_ja_existente_nao_duplica(db_path, tmp_path):
    chave = gerar_chave_valida()
    arquivo = _escrever_arquivo(tmp_path, {chave: _registro_sintetico()})

    primeiro = importar_historico(arquivo, db_path=db_path)
    segundo = importar_historico(arquivo, db_path=db_path)

    assert primeiro.importadas == 1
    assert segundo.importadas == 0
    assert segundo.ja_existentes == 1
    assert len(storage_db.listar_notas(db_path=db_path)) == 1


def test_importar_historico_arquivo_inexistente_levanta_erro(db_path, tmp_path):
    with pytest.raises(ArquivoHistoricoError):
        importar_historico(str(tmp_path / "nao-existe.json"), db_path=db_path)


def test_importar_historico_json_invalido_levanta_erro(db_path, tmp_path):
    caminho = tmp_path / "invalido.json"
    caminho.write_text("{nao e json valido", encoding="utf-8")

    with pytest.raises(ArquivoHistoricoError):
        importar_historico(str(caminho), db_path=db_path)


# --- US3: reexecucao e registro malformado --------------------------------


def test_importar_historico_registro_com_chave_invalida_e_pulado_sem_abortar(db_path, tmp_path):
    chave_valida = gerar_chave_valida()
    dados = {
        "chave-muito-curta": _registro_sintetico(),
        chave_valida: _registro_sintetico(),
    }
    arquivo = _escrever_arquivo(tmp_path, dados)

    resumo = importar_historico(arquivo, db_path=db_path)

    assert resumo.importadas == 1
    assert resumo.puladas == 1
    assert storage_db.buscar_por_chave_acesso(chave_valida, db_path=db_path) is not None


def test_importar_historico_executado_duas_vezes_com_registro_novo_so_adiciona_o_novo(db_path, tmp_path):
    chave_1 = gerar_chave_valida(numero="000000100")
    arquivo = _escrever_arquivo(tmp_path, {chave_1: _registro_sintetico()})
    importar_historico(arquivo, db_path=db_path)

    chave_2 = gerar_chave_valida(numero="000000101")
    arquivo_ampliado = _escrever_arquivo(
        tmp_path, {chave_1: _registro_sintetico(), chave_2: _registro_sintetico()}
    )
    resumo = importar_historico(arquivo_ampliado, db_path=db_path)

    assert resumo.importadas == 1
    assert resumo.ja_existentes == 1
    assert len(storage_db.listar_notas(db_path=db_path)) == 2
