from __future__ import annotations

import pytest
from PIL import Image

from src.services.qrcode_reader import QrCodeIndisponivelError, decodificar_qrcode

qrcode = pytest.importorskip("qrcode", reason="pacote 'qrcode' (dev) ausente para gerar fixture de teste")


def _gerar_imagem_qrcode(conteudo: str) -> Image.Image:
    return qrcode.make(conteudo).convert("RGB")


def test_decodificar_qrcode_le_url_codificada():
    imagem = _gerar_imagem_qrcode("https://www.sefaz.sp.gov.br/nfce/qrcode?p=1234")
    assert decodificar_qrcode(imagem) == "https://www.sefaz.sp.gov.br/nfce/qrcode?p=1234"


def test_decodificar_qrcode_imagem_sem_qrcode_retorna_none():
    imagem = Image.new("RGB", (200, 200), color="white")
    assert decodificar_qrcode(imagem) is None


def test_decodificar_qrcode_aceita_caminho_de_arquivo(tmp_path):
    imagem = _gerar_imagem_qrcode("chave-de-teste-123")
    caminho = tmp_path / "qrcode.png"
    imagem.save(caminho)
    assert decodificar_qrcode(caminho) == "chave-de-teste-123"


def test_decodificar_qrcode_arquivo_invalido_levanta_erro_tratado(tmp_path):
    caminho_invalido = tmp_path / "nao-existe.png"
    with pytest.raises(QrCodeIndisponivelError):
        decodificar_qrcode(caminho_invalido)


def test_decodificar_qrcode_em_imagem_muito_grande():
    """Regressão: fotos de celular em resolução total (confirmado contra
    foto real ~4032x3024) fazem o zbar falhar por causa do tamanho do
    módulo do QR Code em pixels — `decodificar_qrcode` reduz a imagem
    antes de tentar, e isso precisa continuar funcionando."""
    conteudo = "https://www.sefaz.sp.gov.br/nfce/qrcode?p=chave-grande-demais"
    imagem_pequena = _gerar_imagem_qrcode(conteudo)
    imagem_gigante = imagem_pequena.resize((4000, 4000), Image.NEAREST)
    assert decodificar_qrcode(imagem_gigante) == conteudo
