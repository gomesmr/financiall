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


_DIMENSAO_MINIMA_PIXELS = 1500


def _pre_processar(imagem: Image.Image) -> Image.Image:
    """Escala de cinza (research.md #7) e, quando a imagem é pequena
    (fotos de celular de cupons compridos costumam vir com pouca
    resolução por dimensão), amplia com reamostragem LANCZOS antes do
    OCR. Testado contra cupom real: binarização com limiar fixo destrói
    a legibilidade em fotos com iluminação desigual — a ampliação sozinha
    é o que realmente melhora a taxa de reconhecimento, então essa etapa
    de binarização foi removida."""
    cinza = ImageOps.grayscale(imagem)
    menor_lado = min(cinza.width, cinza.height)
    if menor_lado < _DIMENSAO_MINIMA_PIXELS:
        fator = _DIMENSAO_MINIMA_PIXELS / menor_lado
        nova_largura = round(cinza.width * fator)
        nova_altura = round(cinza.height * fator)
        cinza = cinza.resize((nova_largura, nova_altura), Image.LANCZOS)
    return cinza


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
