from __future__ import annotations

import os
import tempfile
from io import BytesIO

from flask import Blueprint, current_app, jsonify, request
from PIL import UnidentifiedImageError
from PIL import Image as PilImage

from src.models.nota_fiscal import TITULARES_VALIDOS
from src.services import chave_acesso as chave_acesso_service
from src.services import exclusao, fila_processamento, importador, importar_extrato_upload, qrcode_reader
from src.services.importar_historico_extrato import processar_transacoes
from src.storage import db as storage_db

bp = Blueprint("importar", __name__)


def _mascarar_chave(chave: str | None) -> str | None:
    return f"...{chave[-4:]}" if chave else None


def _titular_da_requisicao(valor: str | None) -> tuple[str | None, str | None]:
    """Normaliza e valida um valor de `titular` vindo de fora (JSON ou
    form): string vazia é tratada como "não informado" (None), qualquer
    outro valor precisa estar em TITULARES_VALIDOS. Retorna
    (titular, erro) -- erro é None em caso de sucesso."""
    titular = valor or None
    if titular is not None and titular not in TITULARES_VALIDOS:
        return None, "Titular inválido."
    return titular, None


def _item_to_dict(item) -> dict:
    return {
        "codigo_item": item.codigo_item,
        "descricao": item.descricao,
        "quantidade": item.quantidade,
        "valor_unitario": item.valor_unitario,
        "valor_total_item": item.valor_total_item,
    }


def nota_to_dict(nota, itens=None, mascarar_chave: bool = False, categoria=None) -> dict:
    return {
        "id": nota.id,
        "chave_acesso": _mascarar_chave(nota.chave_acesso) if mascarar_chave else nota.chave_acesso,
        "canal_origem": nota.canal_origem.value,
        "uf": nota.uf,
        "cnpj_emitente": nota.cnpj_emitente,
        "emitente_nome": nota.emitente_nome,
        "data_emissao": nota.data_emissao,
        "ano_mes_emissao": nota.ano_mes_emissao,
        "valor_total": nota.valor_total,
        "status": nota.status.value,
        "data_importacao": nota.data_importacao,
        "itens": [_item_to_dict(i) for i in (itens or [])],
        "categoria": {"id": categoria.id, "nome": categoria.nome} if categoria else None,
        "titular": nota.titular,
    }


@bp.post("/notas")
def importar_nota():
    corpo = request.get_json(silent=True) or {}
    entrada = corpo.get("entrada", "")
    if not isinstance(entrada, str) or not entrada.strip():
        return jsonify({"erro": "Nenhuma entrada foi enviada."}), 422

    titular, erro_titular = _titular_da_requisicao(corpo.get("titular"))
    if erro_titular:
        return jsonify({"erro": erro_titular}), 422

    db_path = current_app.config["DB_PATH"]
    try:
        resultado = importador.importar_por_url_ou_chave(entrada, titular=titular, db_path=db_path)
    except chave_acesso_service.ChaveInvalidaError as exc:
        return jsonify({"erro": str(exc)}), 422

    if resultado.status == "ja_registrada":
        return (
            jsonify(
                {
                    "status": "ja_registrada",
                    "mensagem": f"Nota já registrada em {resultado.nota.data_importacao}.",
                    "nota": nota_to_dict(resultado.nota, resultado.itens, mascarar_chave=True),
                }
            ),
            200,
        )

    mensagem = (
        "Nota importada com sucesso."
        if resultado.status == "completa"
        else "Nota importada com dados parciais (pendente de revisão)."
    )
    return (
        jsonify(
            {
                "status": resultado.status,
                "mensagem": mensagem,
                "nota": nota_to_dict(resultado.nota, resultado.itens),
            }
        ),
        201,
    )


@bp.post("/notas/qrcode-frame")
def decodificar_frame_camera():
    """Decodifica um frame de câmera capturado ao vivo pelo navegador
    (feature 007) -- não importa nada, só decodifica. O cliente, ao
    receber uma `entrada` não nula, chama POST /notas separadamente,
    reaproveitando a validação e o fluxo de importação já existentes
    (contracts/api.md)."""
    conteudo = request.get_data()
    if not conteudo:
        return jsonify({"erro": "Não foi possível processar a imagem enviada."}), 415

    try:
        imagem = PilImage.open(BytesIO(conteudo))
        imagem.load()
    except UnidentifiedImageError:
        return jsonify({"erro": "Não foi possível processar a imagem enviada."}), 415

    try:
        entrada = qrcode_reader.decodificar_qrcode(imagem)
    except qrcode_reader.QrCodeIndisponivelError:
        entrada = None

    return jsonify({"entrada": entrada}), 200


@bp.post("/notas/upload")
def upload_nota():
    arquivo = request.files.get("arquivo")
    if arquivo is None or not arquivo.filename:
        return jsonify({"erro": "Nenhum arquivo foi enviado."}), 400

    titular, erro_titular = _titular_da_requisicao(request.form.get("titular"))
    if erro_titular:
        return jsonify({"erro": erro_titular}), 422

    conteudo = arquivo.read()
    db_path = current_app.config["DB_PATH"]
    upload_dir = current_app.config["UPLOAD_DIR"]

    try:
        envio_id = fila_processamento.enfileirar_envio(
            arquivo.filename, conteudo, titular=titular, db_path=db_path, upload_dir=upload_dir
        )
    except fila_processamento.TipoArquivoNaoSuportadoError as exc:
        return jsonify({"erro": str(exc)}), 415

    return (
        jsonify(
            {
                "envio_id": envio_id,
                "status": "pendente",
                "mensagem": f"Arquivo recebido. Consulte o status em /envios/{envio_id}.",
            }
        ),
        202,
    )


@bp.post("/extratos/upload")
def upload_extrato():
    """Upload de extrato/fatura bancária (feature 013) -- síncrono,
    diferente de `/notas/upload`: nenhum dos 4 parsers usa OCR, então o
    processamento inteiro (detecção de formato + parsing + persistência)
    acontece na própria requisição, sem fila (research.md #4). Detecta o
    formato automaticamente (research.md #1/#2) e reaproveita
    `processar_transacoes()` sem alteração -- mesma classificação e
    reconciliação já usadas pelos scripts CLI (FR-006)."""
    arquivo = request.files.get("arquivo")
    if arquivo is None or not arquivo.filename:
        return jsonify({"erro": "Nenhum arquivo foi enviado."}), 400

    db_path = current_app.config["DB_PATH"]

    with tempfile.TemporaryDirectory() as diretorio_temporario:
        # Preserva o nome original (nao um nome temporario aleatorio) --
        # os parsers usam `os.path.basename(caminho)` como "fonte" da
        # transacao.
        caminho = os.path.join(diretorio_temporario, os.path.basename(arquivo.filename))
        arquivo.save(caminho)

        try:
            formato, registros = importar_extrato_upload.detectar_e_parsear(caminho, arquivo.filename)
        except importar_extrato_upload.FormatoNaoReconhecidoError as exc:
            return jsonify({"erro": str(exc)}), 415
        except Exception as exc:  # arquivo corrompido/ilegivel para o parser do formato detectado (Principio III)
            return jsonify({"erro": f"Não foi possível interpretar o arquivo: {exc}"}), 422

    resumo = processar_transacoes(registros, db_path=db_path)

    return (
        jsonify(
            {
                "formato_detectado": formato,
                "importadas": resumo.importadas,
                "ja_existentes": resumo.ja_existentes,
                "puladas": resumo.puladas,
                "classificadas_automaticamente": resumo.classificadas_automaticamente,
                "pendentes_natureza": resumo.pendentes_natureza,
                "reconciliadas": resumo.reconciliadas,
                "ambiguas": resumo.ambiguas,
            }
        ),
        200,
    )


@bp.put("/notas/<int:nota_id>/titular")
def atribuir_titular_a_nota(nota_id: int):
    db_path = current_app.config["DB_PATH"]
    corpo = request.get_json(silent=True) or {}
    titular = corpo.get("titular") or None

    resultado = storage_db.atribuir_titular_a_nota(nota_id, titular, db_path=db_path)
    if resultado is None:
        return jsonify({"erro": "Nota não encontrada."}), 404
    if resultado is False:
        return jsonify({"erro": "Titular inválido."}), 422
    return jsonify({"mensagem": "Titular da nota atualizado com sucesso."}), 200


@bp.delete("/notas/<int:nota_id>")
def excluir_nota(nota_id: int):
    db_path = current_app.config["DB_PATH"]
    excluida = exclusao.excluir_nota_fiscal(nota_id, db_path=db_path)
    if not excluida:
        return jsonify({"erro": "Nota não encontrada."}), 404
    return jsonify({"mensagem": "Nota excluída com sucesso."}), 200
