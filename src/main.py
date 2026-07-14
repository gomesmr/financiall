from __future__ import annotations

import os

from waitress import serve

from src.api.app import create_app
from src.worker.ocr_worker import OcrWorker

app = create_app()


def main() -> None:
    porta = int(os.environ.get("FINANCIALL_PORT", "5000"))
    worker = OcrWorker(db_path=app.config["DB_PATH"])
    worker.iniciar()
    try:
        serve(app, host="0.0.0.0", port=porta, threads=4)
    finally:
        worker.parar()


if __name__ == "__main__":
    main()
