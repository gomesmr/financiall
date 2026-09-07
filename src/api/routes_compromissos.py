from __future__ import annotations

from flask import Blueprint, current_app, jsonify, render_template, request

from src.services import compromissos_futuros as compromissos_service
from src.storage import db as storage_db

bp = Blueprint("compromissos", __name__)


def compromisso_to_dict(compromisso) -> dict:
    return {
        "id": compromisso.id,
        "descricao": compromisso.descricao,
        "valor_parcela": compromisso.valor_parcela,
        "parcela_atual": compromisso.parcela_atual,
        "total_parcelas": compromisso.total_parcelas,
        "mes_referencia": compromisso.mes_referencia,
        "conta": compromisso.conta,
        "titular": compromisso.titular,
    }


@bp.get("/ver/compromissos-futuros")
def pagina_compromissos_futuros():
    db_path = current_app.config["DB_PATH"]
    compromissos = storage_db.listar_compromissos_futuros(apenas_ativos=True, db_path=db_path)
    projecao = compromissos_service.projetar_compromissos_futuros(db_path=db_path)
    return render_template(
        "compromissos_futuros.html",
        compromissos=compromissos,
        projecao=projecao,
        pagina_ativa="compromissos_futuros",
    )


@bp.post("/compromissos-futuros")
def criar_compromisso_futuro():
    db_path = current_app.config["DB_PATH"]
    corpo = request.get_json(silent=True) or {}

    try:
        valor_parcela = round(float(corpo.get("valor_parcela")) * 100)
    except (TypeError, ValueError):
        return jsonify({"erro": "Valor da parcela inválido."}), 422
    try:
        parcela_atual = int(corpo.get("parcela_atual"))
        total_parcelas = int(corpo.get("total_parcelas"))
    except (TypeError, ValueError):
        return jsonify({"erro": "Parcela atual/total de parcelas devem ser números inteiros."}), 422

    compromisso_id, erro = compromissos_service.validar_e_criar_compromisso(
        descricao=corpo.get("descricao", ""),
        valor_parcela=valor_parcela,
        parcela_atual=parcela_atual,
        total_parcelas=total_parcelas,
        mes_referencia=corpo.get("mes_referencia", ""),
        conta=corpo.get("conta"),
        titular=corpo.get("titular"),
        db_path=db_path,
    )
    if erro is not None:
        return jsonify({"erro": erro}), 422

    criado = storage_db.buscar_compromisso_futuro_por_id(compromisso_id, db_path=db_path)
    return (
        jsonify({"mensagem": "Compromisso cadastrado com sucesso.", "compromisso": compromisso_to_dict(criado)}),
        201,
    )


@bp.post("/compromissos-futuros/<int:compromisso_id>/quitar")
def quitar_compromisso_futuro(compromisso_id: int):
    db_path = current_app.config["DB_PATH"]
    sucesso = storage_db.desativar_compromisso_futuro(compromisso_id, db_path=db_path)
    if not sucesso:
        return jsonify({"erro": "Compromisso não encontrado."}), 404
    return jsonify({"mensagem": "Compromisso marcado como quitado/cancelado."}), 200


@bp.delete("/compromissos-futuros/<int:compromisso_id>")
def excluir_compromisso_futuro(compromisso_id: int):
    db_path = current_app.config["DB_PATH"]
    sucesso = storage_db.excluir_compromisso_futuro(compromisso_id, db_path=db_path)
    if not sucesso:
        return jsonify({"erro": "Compromisso não encontrado."}), 404
    return jsonify({"mensagem": "Compromisso excluído com sucesso."}), 200
