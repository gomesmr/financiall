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
    navegador, com a mesma navegacao principal das demais paginas.

    Sem `mes` explicito, as notas aparecem agrupadas visualmente por mes
    (US4, FR-007). `estabelecimento` (categoria_id) filtra pelo tipo de
    estabelecimento da nota, usado pelo drill-down a partir do resumo
    (US3, FR-006)."""
    db_path = current_app.config["DB_PATH"]
    mes = request.args.get("mes")
    titular = request.args.get("titular")
    estabelecimento_raw = request.args.get("estabelecimento")
    estabelecimento_id = int(estabelecimento_raw) if estabelecimento_raw and estabelecimento_raw.isdigit() else None
    notas = storage_db.listar_notas(
        mes=mes, titular=titular, categoria_id=estabelecimento_id, db_path=db_path
    )
    categorias = storage_db.listar_categorias(db_path=db_path)
    categorias_por_id = {c.id: c.nome for c in categorias}
    estabelecimento_nome = categorias_por_id.get(estabelecimento_id) if estabelecimento_id else None
    grupos_por_mes = resumo_service.agrupar_notas_por_mes(notas) if not mes else None
    return render_template(
        "notas.html",
        notas=notas,
        grupos_por_mes=grupos_por_mes,
        categorias_por_id=categorias_por_id,
        titular_filtro=titular,
        mes_filtro=mes,
        estabelecimento_filtro=estabelecimento_id,
        estabelecimento_nome=estabelecimento_nome,
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
    transacao_reconciliada = storage_db.buscar_transacao_por_nota_fiscal_id(nota_id, db_path=db_path)
    return render_template(
        "nota_detalhe.html",
        nota=nota,
        itens=itens,
        categorias=categorias,
        categorias_por_id=categorias_por_id,
        categorias_json=categorias_json,
        transacao_reconciliada=transacao_reconciliada,
        pagina_ativa="notas",
    )


@bp.get("/ver/resumo")
def pagina_resumo():
    """Visao HTML de navegacao do resumo mensal (feature 005, redesenhada na
    feature 009): navegacao unificada por mes (US2), gasto por categoria do
    item com fallback para a categoria da nota (US1) ou por tipo de
    estabelecimento (US5), com toggle de nivel 1/2 (FR-009)."""
    db_path = current_app.config["DB_PATH"]
    mes_atual = resumo_service.mes_atual()
    meses_com_notas = resumo_service.listar_meses_com_notas(db_path=db_path)

    mes_selecionado = request.args.get("mes") or mes_atual
    meses_navegaveis = sorted({mes_atual, mes_selecionado, *meses_com_notas}, reverse=True)
    idx = meses_navegaveis.index(mes_selecionado)
    mes_anterior = meses_navegaveis[idx + 1] if idx + 1 < len(meses_navegaveis) else None
    mes_seguinte = meses_navegaveis[idx - 1] if idx > 0 else None
    mes_mais_recente = meses_navegaveis[0]

    dimensao = request.args.get("dimensao")
    if dimensao not in ("item", "estabelecimento", "ambos"):
        dimensao = "item"
    nivel = 2 if request.args.get("nivel") == "2" else 1

    resumo_mes_selecionado = resumo_service.resumo_de_mes(mes_selecionado, db_path=db_path)
    saldo_mes_selecionado = resumo_service.saldo_do_mes(mes_selecionado, db_path=db_path)

    # Evolucao mensal (feature 005) -- mantida como visao complementar de
    # longo prazo abaixo da navegacao principal, sem sobrepor a ela.
    historico = resumo_service.historico_meses_anteriores(db_path=db_path)
    historico_json = [{"mes": r.mes, "total_gasto": r.total_gasto} for r in historico]

    return render_template(
        "resumo.html",
        mes_selecionado=mes_selecionado,
        mes_atual=mes_atual,
        mes_anterior=mes_anterior,
        mes_seguinte=mes_seguinte,
        mes_mais_recente=mes_mais_recente,
        tem_mes_anterior=mes_anterior is not None,
        tem_mes_seguinte=mes_seguinte is not None,
        dimensao=dimensao,
        nivel=nivel,
        resumo_mes=resumo_mes_selecionado,
        saldo_mes=saldo_mes_selecionado,
        historico=historico,
        historico_json=historico_json,
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
    """Contrato estendido na feature 009 (contracts/api.md): `dimensao`
    (item|estabelecimento, default item) e `nivel` (1|2, default 1). Valor
    invalido de qualquer um dos dois cai silenciosamente no default —
    endpoint de uso interno da propria pagina, sem consumidor externo."""
    db_path = current_app.config["DB_PATH"]
    mes = request.args.get("mes") or resumo_service.mes_atual()
    dimensao = request.args.get("dimensao")
    if dimensao not in ("item", "estabelecimento"):
        dimensao = "item"
    nivel = 2 if request.args.get("nivel") == "2" else 1

    if dimensao == "estabelecimento":
        gastos = resumo_service.gasto_por_estabelecimento(mes, nivel=nivel, db_path=db_path)
    else:
        gastos = resumo_service.gasto_por_categoria_item(mes, nivel=nivel, db_path=db_path)

    return (
        jsonify(
            {
                "mes": mes,
                "dimensao": dimensao,
                "nivel": nivel,
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
