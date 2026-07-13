from __future__ import annotations

from src.services.sefaz_client import _parsear_html

# Trecho reduzido, no formato real confirmado contra um portal de UF (SP):
# layout de referencia nacional com spans txtTit/RCod/Rqtd/RvlUnit/valor
# para itens, e "Valor a pagar R$:" (nao "Valor Total") para o total geral.
HTML_PORTAL_REAL_REDUZIDO = """
<html><body>
<h1 class="tit"><p>DOCUMENTO AUXILIAR DA NOTA FISCAL DE CONSUMIDOR ELETRÔNICA</p></h1>
<div class="txtCenter">
  <div id="u20" class="txtTopo">LOJA EXEMPLO REAL LTDA</div>
  <div class="text">CNPJ: 12.345.678/0001-99</div>
</div>
<table id="tabResult">
  <tr id="Item + 1">
    <td valign="top">
      <span class="txtTit">PRODUTO TESTE UM</span>
      <span class="RCod">(Código: 111)</span>
      <br>
      <span class="Rqtd"><strong>Qtde.:</strong>2,000</span>
      <span class="RUN"><strong>UN: </strong>un</span>
      <span class="RvlUnit"><strong>Vl. Unit.:</strong> 5,00</span>
    </td>
    <td align="right" valign="top" class="txtTit noWrap">
      Vl. Total<br><span class="valor">10,00</span></td>
  </tr>
  <tr id="Item + 2">
    <td valign="top">
      <span class="txtTit">PRODUTO TESTE DOIS</span>
      <span class="RCod">(Código: 222)</span>
      <br>
      <span class="Rqtd"><strong>Qtde.:</strong>1</span>
      <span class="RUN"><strong>UN: </strong>un</span>
      <span class="RvlUnit"><strong>Vl. Unit.:</strong> 3,50</span>
    </td>
    <td align="right" valign="top" class="txtTit noWrap">
      Vl. Total<br><span class="valor">3,50</span></td>
  </tr>
</table>
<div id="totalNota">
  <div id="linhaTotal"><label>Qtd. total de itens:</label><span class="totalNumb">2</span></div>
  <div id="linhaTotal"><label>Valor a pagar R$:</label><span class="totalNumb txtMax">13,50</span></div>
</div>
<div>
  <strong>EMISSÃO NORMAL</strong>
  <strong>Número: </strong>123<strong> Série: </strong>1<strong> Emissão: </strong>10/06/2026 12:00:00
</div>
</body></html>
"""


def test_parsear_html_portal_real_extrai_emitente_via_cabecalho_nacional():
    dados = _parsear_html(HTML_PORTAL_REAL_REDUZIDO)
    assert dados.emitente_nome == "LOJA EXEMPLO REAL LTDA"


def test_parsear_html_portal_real_extrai_valor_a_pagar_como_total():
    dados = _parsear_html(HTML_PORTAL_REAL_REDUZIDO)
    assert dados.valor_total == 1350


def test_parsear_html_portal_real_extrai_data_emissao():
    dados = _parsear_html(HTML_PORTAL_REAL_REDUZIDO)
    assert dados.data_emissao == "2026-06-10"


def test_parsear_html_portal_real_extrai_itens_via_spans_nacionais():
    dados = _parsear_html(HTML_PORTAL_REAL_REDUZIDO)
    assert len(dados.itens) == 2
    assert dados.itens[0] == {
        "codigo_item": "111",
        "descricao": "PRODUTO TESTE UM",
        "quantidade": 2.0,
        "valor_unitario": 500,
        "valor_total_item": 1000,
    }
    assert dados.itens[1]["valor_total_item"] == 350


def test_parsear_html_sem_estrutura_conhecida_retorna_campos_none():
    dados = _parsear_html("<html><body><p>Pagina generica sem dados de nota</p></body></html>")
    assert dados.emitente_nome is None
    assert dados.valor_total is None
    assert dados.itens == []
