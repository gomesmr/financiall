from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from src.api.app import create_app


@pytest.fixture()
def app_e_db():
    """App Flask com um banco SQLite e diretório de upload temporários,
    isolados por teste."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="financiall_test_"))
    db_path = str(tmp_dir / "financiall_test.db")
    upload_dir = str(tmp_dir / "uploads")
    app = create_app(db_path=db_path, upload_dir=upload_dir)
    app.config["TESTING"] = True
    yield app, db_path
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture()
def client(app_e_db):
    app, _ = app_e_db
    return app.test_client()
