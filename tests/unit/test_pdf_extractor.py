from __future__ import annotations

import pytest

from src.services.pdf_extractor import PdfInvalidoError, converter_pdf_em_imagens, poppler_disponivel


def test_converter_pdf_invalido_levanta_erro_tratado(tmp_path):
    caminho_invalido = tmp_path / "nao-e-um-pdf.pdf"
    caminho_invalido.write_bytes(b"isto nao e um PDF valido")
    with pytest.raises(PdfInvalidoError):
        converter_pdf_em_imagens(caminho_invalido)


@pytest.mark.skipif(not poppler_disponivel(), reason="poppler-utils (pdftoppm) não instalado neste ambiente")
def test_converter_pdf_arquivo_inexistente_levanta_erro_tratado(tmp_path):
    with pytest.raises(PdfInvalidoError):
        converter_pdf_em_imagens(tmp_path / "nao-existe.pdf")
