from __future__ import annotations

import pytest

from src.services.chave_acesso import (
    ChaveInvalidaError,
    decodificar_chave,
    extrair_chave_de_url,
    extrair_e_validar,
    normalizar_chave_colada,
)

CHAVE_VALIDA = "35260612345678000199650010000001231000000013"


def test_chave_valida_tem_44_digitos():
    assert len(CHAVE_VALIDA) == 44
    assert CHAVE_VALIDA.isdigit()


def test_extrair_e_validar_aceita_chave_colada():
    assert extrair_e_validar(CHAVE_VALIDA) == CHAVE_VALIDA


def test_extrair_e_validar_normaliza_espacos_e_pontuacao():
    entrada = " 3526 0612.3456-7800 0199 6500 1000 0001 2310 0000 0013 "
    assert extrair_e_validar(entrada) == CHAVE_VALIDA


def test_extrair_e_validar_rejeita_comprimento_incorreto():
    with pytest.raises(ChaveInvalidaError):
        extrair_e_validar("12345")


def test_extrair_e_validar_rejeita_digito_verificador_invalido():
    chave_com_dv_errado = CHAVE_VALIDA[:-1] + str((int(CHAVE_VALIDA[-1]) + 1) % 10)
    with pytest.raises(ChaveInvalidaError, match="dígito verificador inválido"):
        extrair_e_validar(chave_com_dv_errado)


def test_extrair_chave_de_url_encontra_chave_no_parametro_p():
    url = f"https://www.sefaz.sp.gov.br/nfce/qrcode?p={CHAVE_VALIDA}|2|1|1|abcdef"
    assert extrair_chave_de_url(url) == CHAVE_VALIDA


def test_extrair_chave_de_url_retorna_none_sem_chave_valida():
    assert extrair_chave_de_url("https://exemplo.com/?p=nao-tem-chave-aqui") is None


def test_extrair_e_validar_url_sem_chave_levanta_erro():
    with pytest.raises(ChaveInvalidaError):
        extrair_e_validar("https://exemplo.com/?p=123")


def test_extrair_e_validar_aceita_url_envolvida_em_cdata():
    """Regressão: o conteúdo bruto de um QR Code lido pela câmera (feature
    007) pode vir envolvido em `<![CDATA[...]]>` -- o app nativo de câmera
    do celular nunca expõe esse texto ao redor porque extrai só a URL
    antes de abrir no navegador, mas o decodificador desta aplicação lê o
    conteúdo bruto do código (achado real, QR Code de nota fiscal real)."""
    entrada = f"<![CDATA[https://www.nfce.fazenda.sp.gov.br/qrcode?p={CHAVE_VALIDA}|2|1|1|hashficticio]]>"
    assert extrair_e_validar(entrada) == CHAVE_VALIDA


def test_normalizar_chave_colada_remove_nao_digitos():
    assert normalizar_chave_colada("123.456-789 abc") == "123456789"


def test_decodificar_chave_extrai_uf_cnpj_ano_mes_modelo():
    dados = decodificar_chave(CHAVE_VALIDA)
    assert dados.uf == "SP"
    assert dados.ano_mes_emissao == "2606"
    assert dados.cnpj_emitente == "12345678000199"
    assert dados.modelo == "65"
