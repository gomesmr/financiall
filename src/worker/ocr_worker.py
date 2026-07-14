from __future__ import annotations

import logging
import threading

from PIL import Image

from src.models.nota_fiscal import CanalOrigem
from src.services import campos_ocr as campos_ocr_service
from src.services import chave_acesso as chave_acesso_service
from src.services import fila_processamento, importador, ocr_client, pdf_extractor, qrcode_reader
from src.storage import db as storage_db

logger = logging.getLogger(__name__)

INTERVALO_POLL_SEGUNDOS = 2.0


def _imagens_do_envio(envio) -> list[Image.Image]:
    if envio["tipo_arquivo"] == "pdf":
        return pdf_extractor.converter_pdf_em_imagens(envio["caminho_arquivo"])
    return [Image.open(envio["caminho_arquivo"])]


def _reconhecer_texto_do_envio(envio, imagens: list[Image.Image]) -> str:
    textos = [ocr_client.reconhecer_texto_de_imagem(imagem) for imagem in imagens]
    return "\n".join(textos)


def _tentar_via_qrcode(imagens: list[Image.Image], db_path: str) -> importador.ResultadoImportacao | None:
    """QR Code tem correção de erro embutida (Reed-Solomon) e é bem mais
    robusto que OCR de texto corrido para recuperar a chave de acesso —
    tentado antes do reconhecimento de texto completo. A URL decodificada
    é a mesma URL do canal 1, então reaproveita a mesma orquestração
    (extração/validação de chave, dedup, busca best-effort na SEFAZ),
    só marcando `canal_origem=foto_pdf` porque o usuário enviou uma
    imagem, não colou a URL."""
    for imagem in imagens:
        try:
            conteudo = qrcode_reader.decodificar_qrcode(imagem)
        except qrcode_reader.QrCodeIndisponivelError:
            continue
        if not conteudo:
            continue
        try:
            return importador.importar_por_url_ou_chave(
                conteudo, canal_origem=CanalOrigem.FOTO_PDF, db_path=db_path
            )
        except chave_acesso_service.ChaveInvalidaError:
            continue
    return None


def processar_proximo_envio(db_path: str = storage_db.DEFAULT_DB_PATH) -> bool:
    """Processa um único envio pendente (o mais antigo da fila), se
    houver. Retorna True se processou algo, False se a fila estava vazia.

    Nunca propaga exceção: qualquer falha durante a leitura de QR Code, o
    reconhecimento de texto ou a extração de campos resulta em uma nota
    mínima gravada como `pendente_revisao` (Princípio VII) — o envio
    sempre conclui, nunca fica preso (research.md #11)."""
    envio = storage_db.buscar_proximo_envio_pendente(db_path=db_path)
    if envio is None:
        return False

    envio_id = envio["id"]
    storage_db.atualizar_status_envio(envio_id, "processando", db_path=db_path)

    imagens: list[Image.Image] = []
    try:
        imagens = _imagens_do_envio(envio)
    except Exception:
        logger.exception("Falha ao carregar imagem(ns) do envio id=%s", envio_id)

    resultado = None
    if imagens:
        try:
            resultado = _tentar_via_qrcode(imagens, db_path)
        except Exception:
            logger.exception("Falha ao tentar QR Code no envio id=%s", envio_id)

    if resultado is None:
        try:
            texto = _reconhecer_texto_do_envio(envio, imagens)
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
