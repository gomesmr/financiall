import openpyxl
import pytest

from src.services.importar_extrato_bb import parsear


def _criar_extrato_bb(caminho, linhas):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Extrato Conta"
    ws.append(["Data", "Lançamento", "Detalhes", "N° documento", "Valor", "Tipo Lançamento"])
    for linha in linhas:
        ws.append(linha)
    wb.save(caminho)


@pytest.fixture
def arquivo_extrato(tmp_path):
    def _criar(linhas):
        caminho = tmp_path / "Extrato conta corrente - 012026.xlsx"
        _criar_extrato_bb(caminho, linhas)
        return str(caminho)

    return _criar


def test_pula_linhas_de_saldo(arquivo_extrato):
    caminho = arquivo_extrato(
        [
            ["31/12/2025", "Saldo Anterior", " ", " ", "-500,00", " "],
            ["02/01/2026", "Contr BB Credito Salario", "", "100021000188775", "2.500,00", "Entrada"],
            ["00/00/0000", "Saldo do dia", " ", " ", "0,00", " "],
            # ultima linha do arquivo: mesma natureza de "Saldo do dia", mas com
            # letras espacadas e data/valor validos (achado no dado real) --
            # tambem nao e transacao.
            ["31/01/2026", "S A L D O", " ", " ", "-27,88", " "],
        ]
    )
    registros = parsear(caminho)
    assert len(registros) == 1
    assert registros[0]["descricao"] == "Contr BB Credito Salario"


def test_converte_valor_formato_br(arquivo_extrato):
    caminho = arquivo_extrato(
        [
            ["02/01/2026", "Pgto CDC Renovação", "146571601-BB CRÉDITO RENOVAÇÃO", "860021000686582", "-379,26", "Saída"],
            ["06/01/2026", "13º Salário", "", "x", "1.918,87", "Entrada"],
        ]
    )
    registros = parsear(caminho)
    valores = {r["descricao"]: r["valor_raw"] for r in registros}
    assert valores["Pgto CDC Renovação - 146571601-BB CRÉDITO RENOVAÇÃO"] == -379.26
    assert valores["13º Salário"] == 1918.87


def test_concatena_lancamento_e_detalhes_removendo_prefixo_de_timestamp(arquivo_extrato):
    caminho = arquivo_extrato(
        [
            ["02/01/2026", "Pix - Enviado", "02/01 13:50 INSTITUTO CG CLIN ODONTOL", "10201", "-300,00", "Saída"],
        ]
    )
    registros = parsear(caminho)
    assert registros[0]["descricao"] == "Pix - Enviado - INSTITUTO CG CLIN ODONTOL"


def test_lancamento_sozinho_quando_detalhes_vazio(arquivo_extrato):
    caminho = arquivo_extrato(
        [
            ["02/01/2026", "Cobrança de Juros", "", "511058923", "-17,15", "Saída"],
        ]
    )
    registros = parsear(caminho)
    assert registros[0]["descricao"] == "Cobrança de Juros"


def test_mantem_lancamento_quando_detalhes_e_generico(arquivo_extrato):
    """Achado com dado real: 'Detalhes' nem sempre e mais informativo que
    'Lançamento' -- a tarifa bancaria mensal tem Detalhes generico ('Cobrança
    referente <data>'), quem carrega a informacao util e o Lançamento."""
    caminho = arquivo_extrato(
        [
            ["06/01/2026", "Tarifa Pacote de Serviços", "Cobrança referente 06/01/2026", "830061101770714", "-16,10", "Saída"],
        ]
    )
    registros = parsear(caminho)
    assert registros[0]["descricao"] == "Tarifa Pacote de Serviços - Cobrança referente 06/01/2026"


def test_titular_e_conta_sao_fixos(arquivo_extrato):
    caminho = arquivo_extrato(
        [
            ["02/01/2026", "Contr BB Credito Salario", "", "100021000188775", "2.500,00", "Entrada"],
        ]
    )
    registros = parsear(caminho)
    assert registros[0]["titular"] == "cristine"
    assert registros[0]["conta"] == "BB_Cristine"


def test_pula_linha_sem_valor_reconhecivel(arquivo_extrato):
    caminho = arquivo_extrato(
        [
            ["02/01/2026", "Lançamento estranho", "", "1", "", "Saída"],
        ]
    )
    assert parsear(caminho) == []


def test_fonte_e_o_nome_do_arquivo(arquivo_extrato):
    caminho = arquivo_extrato(
        [
            ["02/01/2026", "Contr BB Credito Salario", "", "100021000188775", "2.500,00", "Entrada"],
        ]
    )
    registros = parsear(caminho)
    assert registros[0]["fonte"] == "Extrato conta corrente - 012026.xlsx"
