from __future__ import annotations

from pathlib import Path

from PIL import Image
from pyzbar.pyzbar import decode as zbar_decode

# zbar detecta QR Code de forma pouco confiavel quando o "modulo" (quadrado
# individual) do codigo fica grande demais em pixels — o que acontece em
# fotos de celular em resolucao total (ex.: 4032x3024). Reduzir a imagem
# antes de tentar decodificar resolve isso na pratica (confirmado contra
# foto real: falhava em 4032x3024, funcionava reduzida para 1500px no lado
# maior). Nao e o mesmo problema do OCR de texto (que quer imagem GRANDE);
# QR Code quer imagem pequena o suficiente para o modulo ficar nitido.
_LADO_MAIOR_ALVO_PIXELS = 1500


class QrCodeIndisponivelError(Exception):
    """Falha ao tentar decodificar um QR Code na imagem — biblioteca
    ausente, imagem corrompida, ou qualquer outro erro do decodificador.
    Sempre capturada explicitamente pelo chamador (Princípio III)."""


def _reduzir_se_grande(imagem: Image.Image) -> Image.Image:
    lado_maior = max(imagem.size)
    if lado_maior <= _LADO_MAIOR_ALVO_PIXELS:
        return imagem
    fator = _LADO_MAIOR_ALVO_PIXELS / lado_maior
    nova_dimensao = (round(imagem.width * fator), round(imagem.height * fator))
    return imagem.resize(nova_dimensao, Image.LANCZOS)


def decodificar_qrcode(imagem: Image.Image | str | Path) -> str | None:
    """Tenta decodificar um QR Code na imagem e retorna o texto decodificado
    (tipicamente a URL do QR Code da nota) — ou None se nenhum QR Code for
    encontrado. QR Code tem correção de erro embutida (Reed-Solomon), o que
    o torna mais robusto que OCR de texto corrido para recuperar a chave de
    acesso mesmo com parte da imagem borrada ou danificada.

    Tenta primeiro numa cópia reduzida da imagem (mais confiável para o
    zbar — ver `_LADO_MAIOR_ALVO_PIXELS`) e, se não encontrar nada, tenta
    de novo na imagem original como último recurso."""
    try:
        if not isinstance(imagem, Image.Image):
            imagem = Image.open(imagem)

        resultados = zbar_decode(_reduzir_se_grande(imagem))
        if not resultados:
            resultados = zbar_decode(imagem)
    except Exception as exc:
        raise QrCodeIndisponivelError(str(exc)) from exc

    for resultado in resultados:
        try:
            return resultado.data.decode("utf-8")
        except UnicodeDecodeError:
            continue
    return None
