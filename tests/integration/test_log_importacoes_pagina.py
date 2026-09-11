from __future__ import annotations

from src.services.importar_historico_extrato import processar_transacoes


def _registro(data: str, descricao: str, valor_raw: float, fonte: str):
    return {
        "data": data,
        "descricao": descricao,
        "valor_raw": valor_raw,
        "conta": "Itaú_CC",
        "fonte": fonte,
        "titular": "marcelo",
    }


def test_pagina_log_importacoes_lista_evento_apos_importacao_real(app_e_db, client):
    _, db_path = app_e_db
    processar_transacoes(
        [_registro("2026-08-05", "COMPRA TESTE", -42.5, "extrato-integracao.xls")],
        db_path=db_path,
    )

    resposta = client.get("/ver/log-importacoes")

    assert resposta.status_code == 200
    corpo = resposta.get_data(as_text=True)
    assert "extrato-integracao.xls" in corpo
    assert "05/08/2026" in corpo


def test_pagina_log_importacoes_sem_evento_mostra_estado_vazio(app_e_db, client):
    resposta = client.get("/ver/log-importacoes")

    assert resposta.status_code == 200
    assert "Nenhuma importação registrada ainda." in resposta.get_data(as_text=True)


def test_pagina_log_importacoes_mostra_mais_recente_primeiro(app_e_db, client):
    _, db_path = app_e_db
    processar_transacoes([_registro("2026-08-01", "PRIMEIRO", -10.0, "arquivo-antigo.xls")], db_path=db_path)
    processar_transacoes([_registro("2026-08-02", "SEGUNDO", -20.0, "arquivo-novo.xls")], db_path=db_path)

    corpo = client.get("/ver/log-importacoes").get_data(as_text=True)

    assert corpo.index("arquivo-novo.xls") < corpo.index("arquivo-antigo.xls")
