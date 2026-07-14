from __future__ import annotations

from waitress import serve

from src.api.app import create_app
from src.worker.ocr_worker import OcrWorker

app = create_app()


def main() -> None:
    worker = OcrWorker(db_path=app.config["DB_PATH"])
    worker.iniciar()
    try:
        serve(app, host="0.0.0.0", port=5000, threads=4)
    finally:
        worker.parar()


if __name__ == "__main__":
    main()
