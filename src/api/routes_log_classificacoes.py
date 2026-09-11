from __future__ import annotations

from flask import Blueprint, current_app, render_template

from src.storage import db as storage_db

bp = Blueprint("log_classificacoes", __name__)


@bp.get("/ver/log-classificacoes")
def pagina_log_classificacoes():
    db_path = current_app.config["DB_PATH"]
    logs = storage_db.listar_logs_classificacao_manual(db_path=db_path)
    categorias_por_id = {c.id: c.nome for c in storage_db.listar_categorias(db_path=db_path)}
    return render_template(
        "log_classificacoes.html",
        logs=logs,
        categorias_por_id=categorias_por_id,
        pagina_ativa="log_classificacoes",
    )
