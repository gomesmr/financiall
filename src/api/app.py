from __future__ import annotations

import os

from flask import Flask

from src.api import filters as filtros_jinja
from src.api.routes_categorias import bp as categorias_bp
from src.api.routes_consulta import bp as consulta_bp
from src.api.routes_importar import bp as importar_bp
from src.api.routes_itens import bp as itens_bp
from src.api.routes_transacoes import bp as transacoes_bp
from src.services import fila_processamento
from src.storage import db as storage_db


def create_app(db_path: str | None = None, upload_dir: str | None = None) -> Flask:
    """Factory da aplicacao Flask. `db_path`/`upload_dir` permitem injetar
    um banco e diretorio de upload dedicados (ex.: arquivos temporarios
    nos testes); por padrao usam as variaveis de ambiente
    `FINANCIALL_DB_PATH`/`FINANCIALL_UPLOAD_DIR` (ver storage/db.py e
    services/fila_processamento.py)."""
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or os.environ.get(
        "FINANCIALL_DB_PATH", storage_db.DEFAULT_DB_PATH
    )
    app.config["UPLOAD_DIR"] = upload_dir or os.environ.get(
        "FINANCIALL_UPLOAD_DIR", fila_processamento.DEFAULT_UPLOAD_DIR
    )

    storage_db.init_db(app.config["DB_PATH"])

    app.jinja_env.filters["data_br"] = filtros_jinja.formatar_data_br
    app.jinja_env.filters["mes_ano_br"] = filtros_jinja.formatar_mes_ano_br
    app.jinja_env.filters["aamm_br"] = filtros_jinja.formatar_aamm_br

    app.register_blueprint(importar_bp)
    app.register_blueprint(consulta_bp)
    app.register_blueprint(categorias_bp)
    app.register_blueprint(itens_bp)
    app.register_blueprint(transacoes_bp)

    return app
