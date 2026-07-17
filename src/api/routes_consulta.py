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
    return render_template("upload.html", pagina_ativa="importar")


@bp.get("/ver/notas")
def pagina_notas():
    """Visao HTML de navegacao (distinta do endpoint JSON GET /notas do
    contrato da API) — lista as notas para o usuario navegar pelo
    navegador, com a mesma navegacao principal das demais paginas."""
    db_path = current_app.config["DB_PATH"]
    mes = request.args.get("mes")
    titular = request.args.get("titular")
    notas = storage_db.listar_notas(mes=mes, titular=titular, db_path=db_path)
    categorias_por_id = {c.id: c.nome for c in storage_db.listar_categorias(db_path=db_path)}
    return render_template(
        "notas.html",
        notas=notas,
        categorias_por_id=categorias_por_id,
        titular_filtro=titular,
        pagina_ativa="notas",
    )


@bp.get("/ver/notas/<int:nota_id>")
def pagina_nota_detalhe(nota_id: int):
    """Visao HTML de detalhe de uma nota — acessada clicando numa linha da
    listagem (/ver/notas), mostra os itens que a listagem nao cabe exibir."""
    db_path = current_app.config["DB_PATH"]
    nota = storage_db.buscar_nota_por_id(nota_id, db_path=db_path)
    if nota is None:
        return render_template("nota_detalhe.html", nota=None, pagina_ativa="notas"), 404
    itens = storage_db.listar_itens_por_nota(nota_id, db_path=db_path)
    categorias = storage_db.listar_categorias(db_path=db_path)
    categorias_por_id = {c.id: c for c in categorias}
    categorias_json = [{"id": c.id, "nome": c.nome, "parent_id": c.parent_id} for c in categorias]
    return render_template(
        "nota_detalhe.html",
        nota=nota,
        itens=itens,
        categorias=categorias,
        categorias_por_id=categorias_por_id,
        categorias_json=categorias_json,
        pagina_ativa="notas",
    )


@bp.get("/ver/resumo")
def pagina_resumo():
    """Visao HTML de navegacao do resumo mensal (mes corrente + historico
    + graficos de pizza/barras, feature 005)."""
    db_path = current_app.config["DB_PATH"]
    mes_corrente = resumo_service.gasto_mes_corrente(db_path=db_path)
    historico = resumo_service.historico_meses_anteriores(db_path=db_path)
    historico_json = [{"mes": r.mes, "total_gasto": r.total_gasto} for r in historico]
    meses_disponiveis = [resumo_service.mes_atual()] + [r.mes for r in historico]
    return render_template(
        "resumo.html",
        mes_corrente=mes_corrente,
        historico=historico,
        historico_json=historico_json,
        meses_disponiveis=meses_disponiveis,
        pagina_ativa="resumo",
    )


@bp.get("/ver/envios/<int:envio_id>")
def pagina_envio(envio_id: int):
    """Visao HTML do status de um envio — atualiza sozinha (meta refresh)
    enquanto pendente/processando, para o link devolvido por `POST
    /notas/upload` ser algo navegavel e nao so um endpoint JSON cru."""
    db_path = current_app.config["DB_PATH"]
    envio = storage_db.buscar_envio_por_id(envio_id, db_path=db_path)
    if envio is None:
        return render_template("envio.html", envio=None, pagina_ativa="importar"), 404

    nota = None
    itens = []
    if envio["nota_fiscal_id"] is not None:
        nota = storage_db.buscar_nota_por_id(envio["nota_fiscal_id"], db_path=db_path)
        itens = storage_db.listar_itens_por_nota(nota.id, db_path=db_path)
    return render_template("envio.html", envio=envio, nota=nota, itens=itens, pagina_ativa="importar")


@bp.get("/notas")
def listar_notas():
    db_path = current_app.config["DB_PATH"]
    mes = request.args.get("mes")
    titular = request.args.get("titular")
    notas = storage_db.listar_notas(mes=mes, titular=titular, db_path=db_path)
    categorias_por_id = {c.id: c for c in storage_db.listar_categorias(db_path=db_path)}
    return (
        jsonify(
            {
                "notas": [
                    nota_to_dict(
                        nota,
                        storage_db.listar_itens_por_nota(nota.id, db_path=db_path),
                        categoria=categorias_por_id.get(nota.categoria_id),
                    )
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


@bp.get("/notas/resumo/categorias")
def resumo_categorias():
    db_path = current_app.config["DB_PATH"]
    mes = request.args.get("mes") or resumo_service.mes_atual()
    gastos = resumo_service.gasto_por_categoria(mes, db_path=db_path)
    return (
        jsonify(
            {
                "mes": mes,
                "categorias": [
                    {"categoria_id": g.categoria_id, "nome": g.nome, "total_gasto": g.total_gasto}
                    for g in gastos
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
