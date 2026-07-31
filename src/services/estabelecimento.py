from __future__ import annotations

import re

from src.storage import db as storage_db

# CNPJ (14 digitos) tentado antes de CPF (11 digitos) porque um CNPJ
# formatado (##.###.###/####-##) sempre contem um trecho que poderia casar
# parcialmente o padrao de CPF -- checar CNPJ primeiro evita capturar so um
# pedaco dele (research.md #9).
_RE_CNPJ = re.compile(r"(?<!\d)\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}(?!\d)")
_RE_CPF = re.compile(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)")


def extrair_documento(descricao: str | None) -> str | None:
    """Extrai um CNPJ (14 digitos) ou CPF (11 digitos) da descricao crua da
    transacao, quando presente -- comum em PIX que traz o documento do
    recebedor (research.md #9). Retorna so os digitos, sem formatacao."""
    if not descricao:
        return None
    match = _RE_CNPJ.search(descricao)
    if match:
        return re.sub(r"\D", "", match.group())
    match = _RE_CPF.search(descricao)
    if match:
        return re.sub(r"\D", "", match.group())
    return None


def resolver_estabelecimento(transacao_id: int, db_path: str = storage_db.DEFAULT_DB_PATH) -> int | None:
    """Cascata de identidade de estabelecimento (research.md #9, FR-017 a
    FR-019): 1) CNPJ da nota reconciliada, 2) documento extraido da propria
    descricao (PIX), 3) fallback por descricao normalizada. Chamada tanto
    na importacao quanto apos uma reconciliacao bem-sucedida -- se a
    transacao ja tinha um estabelecimento por descricao e agora ganha um
    documento, promove/funde em vez de manter duas identidades (FR-019).
    Retorna o estabelecimento_id resolvido, ou None se nao ha informacao
    suficiente (nem documento, nem descricao normalizada)."""
    transacao = storage_db.buscar_transacao_por_id(transacao_id, db_path=db_path)
    if transacao is None:
        return None

    documento = None
    if transacao.nota_fiscal_id is not None:
        nota = storage_db.buscar_nota_por_id(transacao.nota_fiscal_id, db_path=db_path)
        if nota is not None and nota.cnpj_emitente:
            # nota_fiscal.cnpj_emitente vem formatado (##.###.###/####-##);
            # normaliza pra so digitos, senao o mesmo CNPJ vindo por essa
            # via e pela via de PIX (extrair_documento, ja so digitos)
            # nunca bateriam e criariam duas identidades pro mesmo lugar.
            documento = re.sub(r"\D", "", nota.cnpj_emitente)
    if documento is None:
        documento = extrair_documento(transacao.descricao)

    if documento:
        if transacao.estabelecimento_id is not None:
            novo_id = storage_db.promover_estabelecimento_para_documento(
                transacao.estabelecimento_id, documento, db_path=db_path
            )
        else:
            # Antes de criar uma identidade nova por documento, ver se OUTRA
            # transacao com a mesma descricao exata ja resolveu por
            # descricao -- promove ela em vez de deixar duas identidades pro
            # mesmo lugar (bug real: compra reconciliada com nota criava um
            # estabelecimento CNPJ separado do "Varejao" ja nomeado por
            # descricao). So pega match exato -- grafias truncadas
            # diferentes continuam exigindo o merge manual por nome
            # (atribuir_estabelecimento) ou uma faxina pontual.
            candidato_id = None
            if transacao.descricao_normalizada:
                candidato_id = storage_db.buscar_estabelecimento_id_por_descricao(
                    transacao.descricao_normalizada, db_path=db_path
                )
            if candidato_id is not None:
                novo_id = storage_db.promover_estabelecimento_para_documento(
                    candidato_id, documento, db_path=db_path
                )
            else:
                novo_id = storage_db.obter_ou_criar_estabelecimento_por_documento(documento, db_path=db_path)
        storage_db.vincular_transacao_a_estabelecimento(transacao_id, novo_id, db_path=db_path)
        return novo_id

    if transacao.estabelecimento_id is not None:
        return transacao.estabelecimento_id

    if transacao.descricao_normalizada:
        novo_id = storage_db.obter_ou_criar_estabelecimento_por_descricao(
            transacao.descricao_normalizada, db_path=db_path
        )
        storage_db.vincular_transacao_a_estabelecimento(transacao_id, novo_id, db_path=db_path)
        return novo_id

    return None
