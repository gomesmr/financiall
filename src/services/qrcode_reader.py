from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageFilter, ImageOps
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


def _realcada(imagem: Image.Image) -> Image.Image:
    """Escala de cinza + autocontraste + máscara de nitidez -- recupera QR
    Code com impressão degradada (impressora térmica desbotada, módulos
    borrados) que nem a imagem original nem uma cópia só reduzida
    conseguem decodificar. Achado real na validação da feature 007: um QR
    Code pequeno (~1,4cm) de cupom térmico só decodificou depois deste
    realce -- confirmado experimentalmente que autocontraste sozinho não
    basta para esse tipo de degradação (o problema dominante é a perda de
    nitidez nas bordas dos módulos, não só o contraste baixo)."""
    cinza = ImageOps.grayscale(imagem)
    autocontraste = ImageOps.autocontrast(cinza, cutoff=1)
    return autocontraste.filter(ImageFilter.UnsharpMask(radius=2, percent=180, threshold=2))


def decodificar_qrcode(imagem: Image.Image | str | Path) -> str | None:
    """Tenta decodificar um QR Code na imagem e retorna o texto decodificado
    (tipicamente a URL do QR Code da nota) — ou None se nenhum QR Code for
    encontrado. QR Code tem correção de erro embutida (Reed-Solomon), o que
    o torna mais robusto que OCR de texto corrido para recuperar a chave de
    acesso mesmo com parte da imagem borrada ou danificada.

    Tenta, em ordem, até uma das variantes decodificar: cópia reduzida da
    imagem (mais confiável para o zbar — ver `_LADO_MAIOR_ALVO_PIXELS`),
    imagem original, e por fim uma versão com contraste/nitidez realçados
    (`_realcada`) -- último recurso mais custoso, só tentado quando as
    variantes mais simples falham."""
    try:
        if not isinstance(imagem, Image.Image):
            imagem = Image.open(imagem)

        reduzida = _reduzir_se_grande(imagem)
        tentativas = [reduzida, imagem, _realcada(reduzida)]

        resultados: list = []
        for candidata in tentativas:
            resultados = zbar_decode(candidata)
            if resultados:
                break
    except Exception as exc:
        raise QrCodeIndisponivelError(str(exc)) from exc

    for resultado in resultados:
        try:
            return resultado.data.decode("utf-8")
        except UnicodeDecodeError:
            continue
    return None
