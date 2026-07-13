from __future__ import annotations

from flask import Blueprint, current_app, jsonify, render_template, request

from src.api.routes_importar import nota_to_dict
from src.services import resumo as resumo_service
from src.storage import db as storage_db

bp = Blueprint("consulta", __name__)


@bp.get("/")
def pagina_upload():
    """Formulario HTML simples (sem framework de frontend) para importar
    por URL/chave ou enviar foto/PDF direto do navegador do celular, sem
    precisar de curl (Polish, usabilidade do canal de digitalizacao)."""
    return render_template("upload.html")


@bp.get("/notas")
def listar_notas():
    db_path = current_app.config["DB_PATH"]
    mes = request.args.get("mes")
    notas = storage_db.listar_notas(mes=mes, db_path=db_path)
    return (
        jsonify(
            {
                "notas": [
                    nota_to_dict(nota, storage_db.listar_itens_por_nota(nota.id, db_path=db_path))
                    for nota in notas
                ]
            }
        ),
        200,
    )


@bp.get("/notas/resumo/mes-atual")
def resumo_mes_atual():
    db_path = current_app.config["DB_PATH"]
    resumo = resumo_service.gasto_mes_corrente(db_path=db_path)
    if resumo is None:
        return (
            jsonify(
                {
                    "mes": resumo_service.mes_atual(),
                    "total_gasto": None,
                    "quantidade_notas": 0,
                    "parcial": True,
                    "mensagem": "Nenhuma nota importada no mês corrente.",
                }
            ),
            200,
        )
    return (
        jsonify(
            {
                "mes": resumo.mes,
                "total_gasto": resumo.total_gasto,
                "quantidade_notas": resumo.quantidade_notas,
                "parcial": True,
                "mensagem": "Total parcial — reflete apenas notas fiscais importadas.",
            }
        ),
        200,
    )


@bp.get("/notas/resumo/historico")
def resumo_historico():
    db_path = current_app.config["DB_PATH"]
    meses = resumo_service.historico_meses_anteriores(db_path=db_path)
    return (
        jsonify(
            {
                "meses": [
                    {"mes": r.mes, "total_gasto": r.total_gasto, "quantidade_notas": r.quantidade_notas}
                    for r in meses
                ],
                "parcial": True,
            }
        ),
        200,
    )


@bp.get("/envios/<int:envio_id>")
def status_envio(envio_id: int):
    db_path = current_app.config["DB_PATH"]
    envio = storage_db.buscar_envio_por_id(envio_id, db_path=db_path)
    if envio is None:
        return jsonify({"erro": "Envio não encontrado."}), 404

    if envio["status"] in ("pendente", "processando"):
        return jsonify({"status": envio["status"]}), 200

    nota = storage_db.buscar_nota_por_id(envio["nota_fiscal_id"], db_path=db_path)
    itens = storage_db.listar_itens_por_nota(nota.id, db_path=db_path)
    resposta = {
        "status": "concluido",
        "nota_status": nota.status.value,
        "nota": nota_to_dict(nota, itens),
    }
    if nota.status.value == "pendente_revisao":
        resposta["mensagem"] = "Processamento concluído com dados incompletos."
    return jsonify(resposta), 200
