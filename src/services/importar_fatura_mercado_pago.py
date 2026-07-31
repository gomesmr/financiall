from __future__ import annotations

import os
import re

import pdfplumber

# Cabecalho da secao de encargos gerais da fatura (juros, multa, IOF,
# pagamento da fatura anterior) -- nao atribuivel a um cartao especifico
# (research.md #5).
_SECAO_ENCARGOS = "Movimentações na fatura"

# Cabecalho de cada cartao vinculado a fatura, ex.: "Cartão Visa
# [************3258]" -- um por titular principal/adicional (research.md #2).
_RE_CARTAO = re.compile(r"^Cartão\s+\S+\s+\[\*+(\d{4})\]$")

_RE_EMISSAO = re.compile(r"Emitida em:\s*(\d{2})/(\d{2})/(\d{4})")

# Uma linha de lancamento real: "DD/MM <descricao>[ Parcela X de Y] R$
# valor" (sinal "-" opcional para estorno/credito). Validado contra a
# fatura real inteira (research.md #2): captura exatamente as linhas de
# lancamento, sem falso positivo vindo de secoes informativas.
_RE_LANCAMENTO = re.compile(r"^(\d{2})/(\d{2})\s+(.+?)(\s+Parcela\s+\d+\s+de\s+\d+)?\s+(-)?R\$\s*([\d.,]+)$")


class FaturaInvalidaError(Exception):
    """Fatura ilegivel, corrompida, ou sem "Emitida em" reconhecivel --
    aborta a importacao inteira sem gravar nada parcial (Princípio III,
    FR-011)."""


def _valor_para_float(texto: str) -> float:
    """Converte "1.822,04" -> 1822.04 (formato BR: ponto de milhar,
    virgula decimal)."""
    return float(texto.replace(".", "").replace(",", "."))


def _inferir_ano(mes_transacao: int, mes_emissao: int, ano_emissao: int) -> int:
    """O lancamento so traz dia/mes -- o ano e inferido a partir da data
    de emissao da fatura (research.md #3): mes <= mes de emissao cai no
    mesmo ano; mes > mes de emissao (parcela cuja compra original foi no
    ano anterior, ex. fatura de janeiro com parcela de dezembro) cai no
    ano anterior."""
    if mes_transacao <= mes_emissao:
        return ano_emissao
    return ano_emissao - 1


def parsear_texto(texto: str, fonte: str) -> list[dict]:
    """Nucleo do parser, separado de `parsear()` (leitura do PDF) para ser
    testavel com texto sintetico equivalente ao que `pdfplumber` extrai,
    sem depender de gerar um PDF real em teste. Maquina de estados simples
    por cabecalho de secao (research.md #2)."""
    match_emissao = _RE_EMISSAO.search(texto)
    if not match_emissao:
        raise FaturaInvalidaError('Fatura sem "Emitida em" reconhecível — layout inesperado.')
    _dia_emissao, mes_emissao_str, ano_emissao_str = match_emissao.groups()
    mes_emissao = int(mes_emissao_str)
    ano_emissao = int(ano_emissao_str)

    registros: list[dict] = []
    conta_atual: str | None = None
    # Duas viagens de app distintas no mesmo dia podem ter o mesmo valor
    # arredondado (achado real processando a fatura de junho/2026: 3 pares
    # de "DL*99 RIDE" com mesma data/descricao/valor) -- sem disambiguacao,
    # a segunda cairia com fingerprint identico a primeira e seria
    # descartada como duplicata, perdendo um gasto real silenciosamente.
    # Conta ocorrencias de (conta, data, descricao, valor) e so marca a
    # partir da segunda, preservando a descricao original (e o fingerprint
    # ja existente) de quem aparece uma unica vez.
    contador_ocorrencias: dict[tuple[str, str, str, float], int] = {}

    for linha_bruta in texto.splitlines():
        linha = linha_bruta.strip()
        if not linha:
            continue

        if linha == _SECAO_ENCARGOS:
            conta_atual = "MercadoPago"
            continue

        match_cartao = _RE_CARTAO.match(linha)
        if match_cartao:
            conta_atual = f"MercadoPago_{match_cartao.group(1)}"
            continue

        # Cabecalho de tabela ("Data Movimentações Valor em R$") e linha
        # "Total R$ ..." ao final de cada secao de cartao nunca sao
        # lancamento -- ignoradas sem mudar a secao atual.
        if linha.startswith("Data Movimentações") or linha.startswith("Total"):
            continue

        match_lancamento = _RE_LANCAMENTO.match(linha)
        if not match_lancamento:
            continue
        if conta_atual is None:
            # Linha de lancamento fora de qualquer secao reconhecida --
            # degrada ignorando a linha em vez de assumir uma conta
            # (Princípio VII).
            continue

        dia, mes, descricao_base, sufixo_parcela, sinal, valor_texto = match_lancamento.groups()
        # Preserva "Parcela X de Y" na descricao (research.md #4) -- sem
        # isso, parcelas consecutivas da mesma compra teriam fingerprint
        # identico (mesma data original, descricao e valor) e a parcela
        # nova seria descartada como duplicata.
        descricao = (descricao_base + (sufixo_parcela or "")).strip()

        if conta_atual == "MercadoPago" and "pagamento da fatura" in descricao.lower():
            # Ja contabilizado do lado da conta que pagou a fatura
            # anterior -- incluir de novo duplicaria o gasto (research.md #7).
            continue

        ano = _inferir_ano(int(mes), mes_emissao, ano_emissao)
        data_iso = f"{ano:04d}-{mes}-{dia}"

        valor = _valor_para_float(valor_texto)
        if sinal == "-":
            valor = -valor

        chave_ocorrencia = (conta_atual, data_iso, descricao, valor)
        contador_ocorrencias[chave_ocorrencia] = contador_ocorrencias.get(chave_ocorrencia, 0) + 1
        ocorrencia = contador_ocorrencias[chave_ocorrencia]
        descricao_final = descricao if ocorrencia == 1 else f"{descricao} #{ocorrencia}"

        registros.append(
            {
                "data": data_iso,
                "descricao": descricao_final,
                "valor_raw": valor,
                "conta": conta_atual,
                "fonte": fonte,
                # Fatura inteira emitida em nome do Marcelo, mesmo quando
                # ha cartao adicional vinculado (Assumption da spec).
                "titular": "marcelo",
            }
        )

    return registros


def parsear(caminho_arquivo: str) -> list[dict]:
    """Le a fatura de cartao Mercado Pago (.pdf, texto nativo selecionavel
    -- research.md #1) e retorna uma lista de registros no mesmo formato
    aceito por importar_historico_extrato.processar_transacoes."""
    fonte = os.path.basename(caminho_arquivo)
    try:
        with pdfplumber.open(caminho_arquivo) as pdf:
            texto = "\n".join(pagina.extract_text() or "" for pagina in pdf.pages)
    except FaturaInvalidaError:
        raise
    except Exception as exc:
        raise FaturaInvalidaError(f"Não foi possível ler o PDF '{caminho_arquivo}': {exc}") from exc

    return parsear_texto(texto, fonte)
