from __future__ import annotations

from flask import Blueprint, current_app, jsonify, render_template, request

from src.services import classificacao_itens
from src.storage import db as storage_db

bp = Blueprint("itens", __name__)


@bp.get("/itens/pendentes")
def listar_itens_pendentes():
    db_path = current_app.config["DB_PATH"]
    nota_id = request.args.get("nota_id", type=int)
    resultado = storage_db.listar_itens_pendentes(nota_fiscal_id=nota_id, db_path=db_path)
    return jsonify(resultado), 200


@bp.post("/itens/pendentes/classificar-grupo")
def classificar_grupo_pendente():
    db_path = current_app.config["DB_PATH"]
    corpo = request.get_json(silent=True) or {}
    descricao_normalizada = corpo.get("descricao_normalizada", "")
    categoria_id = corpo.get("categoria_id")

    quantidade = storage_db.classificar_grupo_pendente(descricao_normalizada, categoria_id, db_path=db_path)
    if quantidade is None:
        return jsonify({"erro": "Categoria não encontrada."}), 422

    return (
        jsonify(
            {"mensagem": f"{quantidade} itens classificados.", "quantidade_itens_afetados": quantidade}
        ),
        200,
    )


@bp.put("/itens/<int:item_id>/categoria")
def atribuir_categoria_item(item_id: int):
    db_path = current_app.config["DB_PATH"]
    corpo = request.get_json(silent=True) or {}
    categoria_id = corpo.get("categoria_id")

    resultado = storage_db.atribuir_categoria_manual(item_id, categoria_id, db_path=db_path)
    if resultado is None:
        return jsonify({"erro": "Item não encontrado."}), 404
    if resultado is False:
        return jsonify({"erro": "Categoria não encontrada."}), 422

    return jsonify({"mensagem": "Categoria do item atualizada com sucesso."}), 200


@bp.get("/itens/<int:item_id>/impacto-correcao-fonte")
def impacto_correcao_fonte(item_id: int):
    db_path = current_app.config["DB_PATH"]
    impacto = storage_db.calcular_impacto_correcao_fonte(item_id, db_path=db_path)
    if impacto is None:
        return jsonify({"erro": "Item não encontrado."}), 404
    return jsonify(impacto), 200


@bp.post("/itens/<int:item_id>/corrigir-fonte")
def corrigir_fonte(item_id: int):
    db_path = current_app.config["DB_PATH"]
    corpo = request.get_json(silent=True) or {}
    categoria_id = corpo.get("categoria_id")

    if storage_db.calcular_impacto_correcao_fonte(item_id, db_path=db_path) is None:
        return jsonify({"erro": "Item não encontrado."}), 404
    if storage_db.buscar_categoria_por_id(categoria_id, db_path=db_path) is None:
        return jsonify({"erro": "Categoria não encontrada."}), 422

    quantidade = storage_db.corrigir_fonte_e_reclassificar(item_id, categoria_id, db_path=db_path)

    return (
        jsonify({"mensagem": f"{quantidade} itens reclassificados.", "quantidade_itens_afetados": quantidade}),
        200,
    )


@bp.get("/ver/pendentes")
def pagina_pendentes():
    db_path = current_app.config["DB_PATH"]
    dados = storage_db.listar_itens_pendentes(db_path=db_path)
    categorias = storage_db.listar_categorias(db_path=db_path)
    categorias_json = [{"id": c.id, "nome": c.nome, "parent_id": c.parent_id} for c in categorias]
    evolucao = classificacao_itens.obter_evolucao_classificacao(db_path=db_path)
    return render_template(
        "pendentes.html",
        resumo=dados["resumo"],
        grupos=dados["grupos"],
        categorias_json=categorias_json,
        evolucao=evolucao,
        pagina_ativa="pendentes",
    )
