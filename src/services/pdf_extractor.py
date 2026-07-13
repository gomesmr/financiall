from __future__ import annotations

import shutil
from pathlib import Path

from pdf2image import convert_from_path
from PIL import Image


class PdfInvalidoError(Exception):
    """PDF corrompido, sem poppler-utils instalado, ou que não pôde ser
    convertido em imagem. Sempre capturada explicitamente pelo chamador
    (Princípio III)."""


def poppler_disponivel() -> bool:
    """Usado para pular testes que dependem do `pdftoppm` real (mesma
    lógica de research.md #16 aplicada ao poppler, não só ao Tesseract)."""
    return shutil.which("pdftoppm") is not None


def converter_pdf_em_imagens(caminho_pdf: str | Path) -> list[Image.Image]:
    """Converte cada página do PDF em uma imagem (research.md #8), para
    seguir o mesmo pipeline de OCR usado para fotos."""
    try:
        return convert_from_path(str(caminho_pdf))
    except Exception as exc:
        raise PdfInvalidoError(str(exc)) from exc
