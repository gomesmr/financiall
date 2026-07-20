from __future__ import annotations

from flask import Blueprint, current_app, jsonify, render_template, request

from src.storage import db as storage_db

bp = Blueprint("estabelecimentos", __name__)


@bp.get("/estabelecimentos/pendentes")
def listar_estabelecimentos_pendentes():
    db_path = current_app.config["DB_PATH"]
    grupos = storage_db.listar_estabelecimentos_pendentes(db_path=db_path)
    return jsonify({"grupos": grupos}), 200


@bp.put("/estabelecimentos/<int:estabelecimento_id>")
def atribuir_estabelecimento(estabelecimento_id: int):
    db_path = current_app.config["DB_PATH"]
    corpo = request.get_json(silent=True) or {}
    nome_fantasia = (corpo.get("nome_fantasia") or "").strip()
    tipo_categoria_id = corpo.get("tipo_categoria_id")

    if not nome_fantasia:
        return jsonify({"erro": "Informe um nome fantasia."}), 422

    resultado = storage_db.atribuir_estabelecimento(
        estabelecimento_id, nome_fantasia, tipo_categoria_id, db_path=db_path
    )
    if resultado is None:
        return jsonify({"erro": "Estabelecimento não encontrado."}), 404

    return jsonify({"mensagem": "Estabelecimento atualizado com sucesso."}), 200


@bp.get("/ver/estabelecimentos/pendentes")
def pagina_estabelecimentos_pendentes():
    db_path = current_app.config["DB_PATH"]
    grupos = storage_db.listar_estabelecimentos_pendentes(db_path=db_path)
    categorias = storage_db.listar_categorias(db_path=db_path)
    categorias_json = [{"id": c.id, "nome": c.nome, "parent_id": c.parent_id} for c in categorias]
    return render_template(
        "estabelecimentos_pendentes.html",
        grupos=grupos,
        categorias_json=categorias_json,
        pagina_ativa="estabelecimentos_pendentes",
    )
