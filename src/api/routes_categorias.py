from __future__ import annotations

from flask import Blueprint, current_app, jsonify, render_template, request

from src.services import categorias as categorias_service
from src.storage import db as storage_db

bp = Blueprint("categorias", __name__)


def categoria_to_dict(categoria) -> dict:
    return {"id": categoria.id, "nome": categoria.nome, "parent_id": categoria.parent_id}


@bp.get("/ver/categorias")
def pagina_categorias():
    db_path = current_app.config["DB_PATH"]
    categorias = storage_db.listar_categorias(db_path=db_path)
    categorias_topo = [c for c in categorias if c.parent_id is None]
    subcategorias_por_pai: dict[int, list] = {}
    for c in categorias:
        if c.parent_id is not None:
            subcategorias_por_pai.setdefault(c.parent_id, []).append(c)
    categorias_json = [{"id": c.id, "nome": c.nome, "parent_id": c.parent_id} for c in categorias]
    return render_template(
        "categorias.html",
        categorias_topo=categorias_topo,
        subcategorias_por_pai=subcategorias_por_pai,
        categorias_json=categorias_json,
        pagina_ativa="categorias",
    )


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
    parent_id = corpo.get("parent_id")
    forcar = bool(corpo.get("forcar", False))

    categoria_id, erro, aviso = categorias_service.validar_e_criar_categoria(
        nome, parent_id=parent_id, forcar=forcar, db_path=db_path
    )
    if erro is not None:
        return jsonify({"erro": erro}), 422
    if aviso is not None:
        return jsonify(aviso), 409

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


@bp.get("/categorias/<int:categoria_id>/impacto-exclusao")
def impacto_exclusao_categoria(categoria_id: int):
    db_path = current_app.config["DB_PATH"]
    impacto = storage_db.calcular_impacto_exclusao(categoria_id, db_path=db_path)
    if impacto is None:
        return jsonify({"erro": "Categoria não encontrada."}), 404
    return jsonify(impacto), 200


@bp.delete("/categorias/<int:categoria_id>")
def excluir_categoria(categoria_id: int):
    db_path = current_app.config["DB_PATH"]
    impacto = storage_db.calcular_impacto_exclusao(categoria_id, db_path=db_path)
    if impacto is None:
        return jsonify({"erro": "Categoria não encontrada."}), 404

    if impacto["tem_subcategorias"]:
        return jsonify({"erro": "Exclua ou mova as subcategorias antes de excluir esta categoria."}), 422

    em_uso = impacto["quantidade_itens"] > 0 or impacto["quantidade_cache"] > 0 or impacto["quantidade_regras"] > 0

    corpo = request.get_json(silent=True) or {}
    destino = corpo.get("destino")

    if em_uso and destino is None:
        return jsonify({"erro": "Informe o destino dos itens/cache/regras afetados antes de excluir."}), 422

    resultado = storage_db.excluir_categoria_com_destino(
        categoria_id, destino or "pendente", corpo.get("categoria_substituta_id"), db_path=db_path
    )
    if resultado is None:
        return jsonify({"erro": "Categoria não encontrada."}), 404
    if resultado is False:
        return jsonify({"erro": "Não foi possível excluir a categoria com o destino informado."}), 422

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
