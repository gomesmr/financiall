from __future__ import annotations

import shutil
from pathlib import Path

import pytesseract
from PIL import Image, ImageOps


class OcrIndisponivelError(Exception):
    """Falha ao reconhecer texto na imagem — binário do Tesseract ausente,
    imagem corrompida, ou qualquer outro erro do motor de OCR. Sempre
    capturada explicitamente pelo chamador (Princípio III)."""


def tesseract_disponivel() -> bool:
    """Usado para pular testes que dependem do binário real (research.md
    #16) — o desenvolvimento acontece no Windows, onde o Tesseract pode ou
    não estar instalado."""
    return shutil.which("tesseract") is not None


def _pre_processar(imagem: Image.Image) -> Image.Image:
    """Escala de cinza + binarização simples (research.md #7): melhora a
    taxa de reconhecimento sem custo de memória relevante no hardware do
    Raspberry Pi."""
    cinza = ImageOps.grayscale(imagem)
    return cinza.point(lambda pixel: 255 if pixel > 150 else 0)


def reconhecer_texto_de_imagem(imagem: Image.Image, idioma: str = "por") -> str:
    """Reconhece o texto de uma imagem PIL já carregada em memória (usado
    tanto para fotos quanto para páginas de PDF já convertidas pelo
    pdf_extractor). Levanta OcrIndisponivelError em qualquer falha."""
    try:
        imagem_preprocessada = _pre_processar(imagem)
        return pytesseract.image_to_string(imagem_preprocessada, lang=idioma)
    except Exception as exc:
        raise OcrIndisponivelError(str(exc)) from exc


def reconhecer_texto(caminho_imagem: str | Path, idioma: str = "por") -> str:
    """Reconhece o texto de uma imagem a partir de um caminho em disco
    (research.md #7). Levanta OcrIndisponivelError em qualquer falha
    (arquivo corrompido, binário ausente, etc.) — nunca propaga a exceção
    original."""
    try:
        with Image.open(caminho_imagem) as imagem:
            return reconhecer_texto_de_imagem(imagem, idioma=idioma)
    except OcrIndisponivelError:
        raise
    except Exception as exc:
        raise OcrIndisponivelError(str(exc)) from exc
