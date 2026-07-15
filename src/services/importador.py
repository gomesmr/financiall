from __future__ import annotations

from dataclasses import dataclass

from src.models.item_nota import ItemNota
from src.models.nota_fiscal import CanalOrigem, NotaFiscal, StatusNota
from src.services import campos_ocr as campos_ocr_service
from src.services import chave_acesso as chave_acesso_service
from src.services import sefaz_client
from src.storage import db as storage_db


@dataclass(frozen=True)
class ResultadoImportacao:
    status: str  # "completa" | "pendente_revisao" | "ja_registrada"
    nota: NotaFiscal
    itens: list[ItemNota]


def _calcular_status(
    emitente_nome: str | None,
    data_emissao: str | None,
    valor_total: int | None,
    itens: list[ItemNota],
    chave_identificada: bool = True,
) -> StatusNota:
    """`completa` só quando todos os campos best-effort foram obtidos e a
    chave de acesso foi identificada; qualquer ausência marca
    `pendente_revisao` (data-model.md, FR-013)."""
    if not chave_identificada:
        return StatusNota.PENDENTE_REVISAO
    campos_completos = bool(emitente_nome) and bool(data_emissao) and valor_total is not None and bool(itens)
    return StatusNota.COMPLETA if campos_completos else StatusNota.PENDENTE_REVISAO


def importar_por_url_ou_chave(
    entrada: str,
    canal_origem: CanalOrigem = CanalOrigem.URL_CHAVE,
    db_path: str = storage_db.DEFAULT_DB_PATH,
) -> ResultadoImportacao:
    """Orquestra o canal URL/chave: valida a chave, checa duplicidade,
    busca dados best-effort na fonte SEFAZ (só modelo 65) e grava a nota
    (US1, US3, US4). Levanta `chave_acesso.ChaveInvalidaError` quando a
    entrada não resulta em uma chave válida (FR-004) — o chamador (rota da
    API) é responsável por transformar isso numa resposta HTTP 422.

    `canal_origem` permite reaproveitar esta orquestração quando a URL foi
    obtida de outra forma (ex.: QR Code decodificado de uma foto — o
    worker do canal 2 chama esta função com `canal_origem=FOTO_PDF` para
    reusar a mesma busca best-effort na SEFAZ, já que a URL do QR Code é
    idêntica nos dois canais)."""
    chave = chave_acesso_service.extrair_e_validar(entrada)

    existente = storage_db.buscar_por_chave_acesso(chave, db_path=db_path)
    if existente is not None:
        itens_existentes = storage_db.listar_itens_por_nota(existente.id, db_path=db_path)
        return ResultadoImportacao(status="ja_registrada", nota=existente, itens=itens_existentes)

    dados_chave = chave_acesso_service.decodificar_chave(chave)

    url_original = chave_acesso_service.extrair_url(entrada.strip())

    emitente_nome: str | None = None
    data_emissao: str | None = None
    valor_total: int | None = None
    itens: list[ItemNota] = []

    if dados_chave.modelo == "65" and url_original:
        try:
            dados_sefaz = sefaz_client.buscar_dados_nota(url_original)
        except sefaz_client.BuscaSefazIndisponivelError:
            # Fonte fragil: falha nunca impede o registro (Principio VII).
            pass
        else:
            emitente_nome = dados_sefaz.emitente_nome
            data_emissao = dados_sefaz.data_emissao
            valor_total = dados_sefaz.valor_total
            itens = [ItemNota(nota_fiscal_id=0, **item) for item in dados_sefaz.itens]

    status = _calcular_status(emitente_nome, data_emissao, valor_total, itens)

    nota = NotaFiscal(
        canal_origem=canal_origem,
        status=status,
        chave_acesso=chave,
        uf=dados_chave.uf,
        cnpj_emitente=dados_chave.cnpj_emitente,
        ano_mes_emissao=dados_chave.ano_mes_emissao,
        modelo=dados_chave.modelo,
        emitente_nome=emitente_nome,
        data_emissao=data_emissao,
        valor_total=valor_total,
    )
    storage_db.inserir_nota(nota, db_path=db_path)
    for item in itens:
        item.nota_fiscal_id = nota.id
    storage_db.inserir_itens(itens, db_path=db_path)

    return ResultadoImportacao(status=status, nota=nota, itens=itens)


def importar_por_ocr(
    campos: campos_ocr_service.CamposExtraidos,
    hash_conteudo: str,
    db_path: str = storage_db.DEFAULT_DB_PATH,
) -> ResultadoImportacao:
    """Orquestra o canal foto/PDF depois do OCR já ter rodado (chamado pelo
    worker — US2/US3/US4): dedup por chave de acesso quando identificada,
    senão por hash de conteúdo do arquivo; grava a nota com o que houver
    quando não é duplicata (FR-010/FR-013)."""
    existente = None
    if campos.chave_acesso:
        existente = storage_db.buscar_por_chave_acesso(campos.chave_acesso, db_path=db_path)
    if existente is None:
        existente = storage_db.buscar_por_hash_conteudo(hash_conteudo, db_path=db_path)

    if existente is not None:
        itens_existentes = storage_db.listar_itens_por_nota(existente.id, db_path=db_path)
        return ResultadoImportacao(status="ja_registrada", nota=existente, itens=itens_existentes)

    chave_identificada = bool(campos.chave_acesso)
    uf = cnpj_emitente = ano_mes_emissao = modelo = None
    if chave_identificada:
        dados_chave = chave_acesso_service.decodificar_chave(campos.chave_acesso)
        uf = dados_chave.uf
        cnpj_emitente = dados_chave.cnpj_emitente
        ano_mes_emissao = dados_chave.ano_mes_emissao
        modelo = dados_chave.modelo
    else:
        cnpj_emitente = campos.cnpj_emitente

    itens = [ItemNota(nota_fiscal_id=0, **item) for item in campos.itens]
    status = _calcular_status(
        campos.emitente_nome,
        campos.data_emissao,
        campos.valor_total,
        itens,
        chave_identificada=chave_identificada,
    )

    nota = NotaFiscal(
        canal_origem=CanalOrigem.FOTO_PDF,
        status=status,
        chave_acesso=campos.chave_acesso,
        hash_conteudo=None if chave_identificada else hash_conteudo,
        uf=uf,
        cnpj_emitente=cnpj_emitente,
        ano_mes_emissao=ano_mes_emissao,
        modelo=modelo,
        emitente_nome=campos.emitente_nome,
        data_emissao=campos.data_emissao,
        valor_total=campos.valor_total,
    )
    storage_db.inserir_nota(nota, db_path=db_path)
    for item in itens:
        item.nota_fiscal_id = nota.id
    storage_db.inserir_itens(itens, db_path=db_path)

    return ResultadoImportacao(status=status, nota=nota, itens=itens)
