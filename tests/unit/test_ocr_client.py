from __future__ import annotations

import io

import pytest
from PIL import Image, ImageDraw

from src.services.ocr_client import OcrIndisponivelError, reconhecer_texto, tesseract_disponivel


def test_reconhecer_texto_arquivo_inexistente_levanta_erro_tratado(tmp_path):
    caminho_inexistente = tmp_path / "nao-existe.png"
    with pytest.raises(OcrIndisponivelError):
        reconhecer_texto(caminho_inexistente)


@pytest.mark.skipif(not tesseract_disponivel(), reason="Tesseract não instalado neste ambiente")
def test_reconhecer_texto_imagem_real_com_tesseract_instalado(tmp_path):
    imagem = Image.new("RGB", (400, 100), color="white")
    desenho = ImageDraw.Draw(imagem)
    desenho.text((10, 30), "TESTE FINANCIALL", fill="black")
    caminho = tmp_path / "cupom.png"
    imagem.save(caminho)

    texto = reconhecer_texto(caminho, idioma="eng")
    assert isinstance(texto, str)
