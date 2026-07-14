from __future__ import annotations

from flask import Blueprint, current_app, jsonify, render_template, request

from src.services import categorias as categorias_service
from src.storage import db as storage_db

bp = Blueprint("categorias", __name__)


def categoria_to_dict(categoria) -> dict:
    return {"id": categoria.id, "nome": categoria.nome}


@bp.get("/ver/categorias")
def pagina_categorias():
    db_path = current_app.config["DB_PATH"]
    categorias = storage_db.listar_categorias(db_path=db_path)
    return render_template("categorias.html", categorias=categorias, pagina_ativa="categorias")


@bp.get("/categorias")
def listar_categorias():
    db_path = current_app.config["DB_PATH"]
    categorias = storage_db.listar_categorias(db_path=db_path)
    return jsonify({"categorias": [categoria_to_dict(c) for c in categorias]}), 200


@bp.post("/categorias")
def criar_categoria():
    db_path = current_app.config["DB_PATH"]
    corpo = request.get_json(silent=True) or {}
    nome = corpo.get("nome", "")

    categoria_id, erro = categorias_service.validar_e_criar_categoria(nome, db_path=db_path)
    if erro is not None:
        return jsonify({"erro": erro}), 422

    categoria = storage_db.buscar_categoria_por_id(categoria_id, db_path=db_path)
    return (
        jsonify({"mensagem": "Categoria criada com sucesso.", "categoria": categoria_to_dict(categoria)}),
        201,
    )


@bp.put("/categorias/<int:categoria_id>")
def editar_categoria(categoria_id: int):
    db_path = current_app.config["DB_PATH"]
    corpo = request.get_json(silent=True) or {}
    nome = corpo.get("nome", "")

    sucesso, erro = categorias_service.validar_e_editar_categoria(categoria_id, nome, db_path=db_path)
    if sucesso is None:
        return jsonify({"erro": erro}), 404
    if sucesso is False:
        return jsonify({"erro": erro}), 422

    categoria = storage_db.buscar_categoria_por_id(categoria_id, db_path=db_path)
    return (
        jsonify({"mensagem": "Categoria atualizada com sucesso.", "categoria": categoria_to_dict(categoria)}),
        200,
    )


@bp.delete("/categorias/<int:categoria_id>")
def excluir_categoria(categoria_id: int):
    db_path = current_app.config["DB_PATH"]
    excluida = storage_db.excluir_categoria(categoria_id, db_path=db_path)
    if not excluida:
        return jsonify({"erro": "Categoria não encontrada."}), 404
    return jsonify({"mensagem": "Categoria excluída com sucesso."}), 200


@bp.put("/notas/<int:nota_id>/categoria")
def atribuir_categoria_a_nota(nota_id: int):
    db_path = current_app.config["DB_PATH"]
    corpo = request.get_json(silent=True) or {}
    categoria_id = corpo.get("categoria_id")

    resultado = storage_db.atribuir_categoria_a_nota(nota_id, categoria_id, db_path=db_path)
    if resultado is None:
        return jsonify({"erro": "Nota não encontrada."}), 404
    if resultado is False:
        return jsonify({"erro": "Categoria não encontrada."}), 422
    return jsonify({"mensagem": "Categoria da nota atualizada com sucesso."}), 200
