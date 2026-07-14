from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from src.services import chave_acesso as chave_acesso_service
from src.services import fila_processamento, importador

bp = Blueprint("importar", __name__)


def _mascarar_chave(chave: str | None) -> str | None:
    return f"...{chave[-4:]}" if chave else None


def _item_to_dict(item) -> dict:
    return {
        "codigo_item": item.codigo_item,
        "descricao": item.descricao,
        "quantidade": item.quantidade,
        "valor_unitario": item.valor_unitario,
        "valor_total_item": item.valor_total_item,
    }


def nota_to_dict(nota, itens=None, mascarar_chave: bool = False) -> dict:
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
    }


@bp.post("/notas")
def importar_nota():
    corpo = request.get_json(silent=True) or {}
    entrada = corpo.get("entrada", "")
    if not isinstance(entrada, str) or not entrada.strip():
        return jsonify({"erro": "Nenhuma entrada foi enviada."}), 422

    db_path = current_app.config["DB_PATH"]
    try:
        resultado = importador.importar_por_url_ou_chave(entrada, db_path=db_path)
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


@bp.post("/notas/upload")
def upload_nota():
    arquivo = request.files.get("arquivo")
    if arquivo is None or not arquivo.filename:
        return jsonify({"erro": "Nenhum arquivo foi enviado."}), 400

    conteudo = arquivo.read()
    db_path = current_app.config["DB_PATH"]
    upload_dir = current_app.config["UPLOAD_DIR"]

    try:
        envio_id = fila_processamento.enfileirar_envio(
            arquivo.filename, conteudo, db_path=db_path, upload_dir=upload_dir
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
