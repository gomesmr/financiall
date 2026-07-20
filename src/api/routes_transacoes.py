from __future__ import annotations

from flask import Blueprint, current_app, jsonify, render_template, request

from src.models.transacao import NATUREZAS_VALIDAS
from src.storage import db as storage_db

bp = Blueprint("transacoes", __name__)


# --- US4: fila de pendentes de natureza -----------------------------------


@bp.get("/transacoes/pendentes")
def listar_transacoes_pendentes():
    db_path = current_app.config["DB_PATH"]
    resultado = storage_db.listar_transacoes_pendentes_natureza(db_path=db_path)
    return jsonify(resultado), 200


@bp.post("/transacoes/pendentes/classificar-grupo")
def classificar_grupo_pendente_natureza():
    db_path = current_app.config["DB_PATH"]
    corpo = request.get_json(silent=True) or {}
    descricao_normalizada = corpo.get("descricao_normalizada", "")
    natureza = corpo.get("natureza")
    categoria_id = corpo.get("categoria_id")

    if natureza not in NATUREZAS_VALIDAS:
        return jsonify({"erro": "Natureza inválida."}), 422
    if natureza == "gasto" and categoria_id is None:
        return jsonify({"erro": "categoria_id é obrigatório quando natureza é 'gasto'."}), 422

    quantidade = storage_db.classificar_grupo_pendente_natureza(
        descricao_normalizada, natureza, categoria_id, db_path=db_path
    )
    return (
        jsonify({"mensagem": f"{quantidade} transação(ões) classificada(s).", "quantidade_afetada": quantidade}),
        200,
    )


@bp.put("/transacoes/<int:transacao_id>/natureza")
def atribuir_natureza_transacao(transacao_id: int):
    db_path = current_app.config["DB_PATH"]
    corpo = request.get_json(silent=True) or {}
    natureza = corpo.get("natureza")
    categoria_id = corpo.get("categoria_id")

    if natureza not in NATUREZAS_VALIDAS:
        return jsonify({"erro": "Natureza inválida."}), 422
    if natureza == "gasto" and categoria_id is None:
        return jsonify({"erro": "categoria_id é obrigatório quando natureza é 'gasto'."}), 422

    resultado = storage_db.atribuir_natureza_manual(transacao_id, natureza, categoria_id, db_path=db_path)
    if resultado is None:
        return jsonify({"erro": "Transação não encontrada."}), 404
    if resultado is False:
        return jsonify({"erro": "Natureza inválida."}), 422

    return jsonify({"mensagem": "Natureza da transação atualizada com sucesso."}), 200


# --- US3: reconciliacao Nota Fiscal <-> Transacao --------------------------


@bp.get("/transacoes/reconciliacao/pendentes")
def listar_reconciliacoes_pendentes():
    db_path = current_app.config["DB_PATH"]
    casos = storage_db.listar_reconciliacoes_pendentes(db_path=db_path)
    return jsonify({"casos": casos}), 200


@bp.put("/transacoes/<int:transacao_id>/nota")
def vincular_transacao_a_nota(transacao_id: int):
    db_path = current_app.config["DB_PATH"]
    corpo = request.get_json(silent=True) or {}
    nota_fiscal_id = corpo.get("nota_fiscal_id")

    resultado = storage_db.vincular_reconciliacao_manual(transacao_id, nota_fiscal_id, db_path=db_path)
    if resultado is None:
        return jsonify({"erro": "Transação ou nota fiscal não encontrada."}), 404
    if resultado is False:
        return jsonify({"erro": "Nota fiscal já está vinculada a outra transação."}), 422

    return jsonify({"mensagem": "Transação vinculada à nota fiscal com sucesso."}), 200


@bp.delete("/transacoes/<int:transacao_id>/nota")
def desvincular_transacao_de_nota(transacao_id: int):
    db_path = current_app.config["DB_PATH"]
    resultado = storage_db.desvincular_reconciliacao(transacao_id, db_path=db_path)
    if resultado is None:
        return jsonify({"erro": "Transação não encontrada ou sem nota vinculada."}), 404
    return jsonify({"mensagem": "Vínculo com a nota fiscal desfeito com sucesso."}), 200


# --- Pagina de revisao (US3 + US4) ------------------------------------------


@bp.get("/ver/transacoes/pendentes")
def pagina_transacoes_pendentes():
    db_path = current_app.config["DB_PATH"]
    dados = storage_db.listar_transacoes_pendentes_natureza(db_path=db_path)
    casos_ambiguos = storage_db.listar_reconciliacoes_pendentes(db_path=db_path)
    categorias = storage_db.listar_categorias(db_path=db_path)
    categorias_json = [{"id": c.id, "nome": c.nome, "parent_id": c.parent_id} for c in categorias]
    return render_template(
        "transacoes_pendentes.html",
        resumo=dados["resumo"],
        grupos=dados["grupos"],
        casos_ambiguos=casos_ambiguos,
        categorias_json=categorias_json,
        naturezas=sorted(NATUREZAS_VALIDAS),
        pagina_ativa="transacoes_pendentes",
    )
