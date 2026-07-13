from __future__ import annotations

import logging
import threading

from src.services import campos_ocr as campos_ocr_service
from src.services import fila_processamento, importador, ocr_client, pdf_extractor
from src.storage import db as storage_db

logger = logging.getLogger(__name__)

INTERVALO_POLL_SEGUNDOS = 2.0


def _reconhecer_texto_do_envio(envio) -> str:
    if envio["tipo_arquivo"] == "pdf":
        paginas = pdf_extractor.converter_pdf_em_imagens(envio["caminho_arquivo"])
        textos = [ocr_client.reconhecer_texto_de_imagem(pagina) for pagina in paginas]
        return "\n".join(textos)
    return ocr_client.reconhecer_texto(envio["caminho_arquivo"])


def processar_proximo_envio(db_path: str = storage_db.DEFAULT_DB_PATH) -> bool:
    """Processa um único envio pendente (o mais antigo da fila), se
    houver. Retorna True se processou algo, False se a fila estava vazia.

    Nunca propaga exceção: qualquer falha durante o reconhecimento de
    texto ou a extração de campos resulta em uma nota mínima gravada como
    `pendente_revisao` (Princípio VII) — o envio sempre conclui, nunca
    fica preso (research.md #11)."""
    envio = storage_db.buscar_proximo_envio_pendente(db_path=db_path)
    if envio is None:
        return False

    envio_id = envio["id"]
    storage_db.atualizar_status_envio(envio_id, "processando", db_path=db_path)

    try:
        texto = _reconhecer_texto_do_envio(envio)
        campos = campos_ocr_service.extrair_campos(texto)
    except Exception:
        logger.exception("Falha ao processar envio id=%s; gravando nota mínima", envio_id)
        campos = campos_ocr_service.CamposExtraidos()

    resultado = importador.importar_por_ocr(campos, envio["hash_conteudo"], db_path=db_path)

    storage_db.atualizar_status_envio(
        envio_id,
        "concluido",
        nota_fiscal_id=resultado.nota.id,
        marcar_processado_agora=True,
        db_path=db_path,
    )
    return True


class OcrWorker:
    """Worker sequencial (um item por vez, sem paralelismo — research.md
    #10), rodando em uma thread de background dentro do mesmo processo do
    servidor HTTP."""

    def __init__(
        self,
        db_path: str = storage_db.DEFAULT_DB_PATH,
        intervalo_poll: float = INTERVALO_POLL_SEGUNDOS,
    ) -> None:
        self._db_path = db_path
        self._intervalo_poll = intervalo_poll
        self._parar = threading.Event()
        self._thread: threading.Thread | None = None

    def iniciar(self) -> None:
        fila_processamento.reconciliar_fila_apos_reinicio(db_path=self._db_path)
        self._thread = threading.Thread(target=self._loop, daemon=True, name="ocr-worker")
        self._thread.start()

    def parar(self) -> None:
        self._parar.set()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def _loop(self) -> None:
        while not self._parar.is_set():
            try:
                processou = processar_proximo_envio(db_path=self._db_path)
            except Exception:
                logger.exception("Erro inesperado no loop do worker de OCR")
                processou = False
            if not processou:
                self._parar.wait(self._intervalo_poll)
