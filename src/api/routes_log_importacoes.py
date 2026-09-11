from __future__ import annotations

from flask import Blueprint, current_app, render_template

from src.storage import db as storage_db

bp = Blueprint("log_importacoes", __name__)


@bp.get("/ver/log-importacoes")
def pagina_log_importacoes():
    db_path = current_app.config["DB_PATH"]
    logs = storage_db.listar_logs_importacao(db_path=db_path)
    return render_template("log_importacoes.html", logs=logs, pagina_ativa="log_importacoes")
