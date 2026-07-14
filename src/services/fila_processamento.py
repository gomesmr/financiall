from __future__ import annotations

import hashlib
import os
import uuid
from pathlib import Path

from src.storage import db as storage_db

DEFAULT_UPLOAD_DIR = os.environ.get("FINANCIALL_UPLOAD_DIR", "data/uploads")

_EXTENSOES_POR_TIPO = {
    "foto": {".jpg", ".jpeg", ".png"},
    "pdf": {".pdf"},
}


class TipoArquivoNaoSuportadoError(ValueError):
    """Arquivo enviado não é nem imagem nem PDF (FR-005, contrato: 415)."""


def _tipo_arquivo(nome_arquivo: str) -> str:
    extensao = Path(nome_arquivo).suffix.lower()
    for tipo, extensoes in _EXTENSOES_POR_TIPO.items():
        if extensao in extensoes:
            return tipo
    raise TipoArquivoNaoSuportadoError(
        f"Tipo de arquivo não suportado ({extensao or 'sem extensão'}). Envie uma foto ou um PDF."
    )


def calcular_hash_conteudo(conteudo: bytes) -> str:
    """SHA-256 sobre os bytes brutos do arquivo (research.md #12) — sempre
    calculável, independentemente do sucesso do OCR."""
    return hashlib.sha256(conteudo).hexdigest()


def salvar_arquivo_recebido(
    nome_original: str, conteudo: bytes, upload_dir: str = DEFAULT_UPLOAD_DIR
) -> tuple[str, str]:
    """Grava o arquivo em disco com um nome único (evita colisão entre
    envios) e retorna (caminho, tipo_arquivo). Levanta
    TipoArquivoNaoSuportadoError se a extensão não for imagem nem PDF."""
    tipo = _tipo_arquivo(nome_original)
    Path(upload_dir).mkdir(parents=True, exist_ok=True)
    extensao = Path(nome_original).suffix.lower()
    caminho = str(Path(upload_dir) / f"{uuid.uuid4().hex}{extensao}")
    with open(caminho, "wb") as arquivo:
        arquivo.write(conteudo)
    return caminho, tipo


def enfileirar_envio(
    nome_original: str,
    conteudo: bytes,
    db_path: str = storage_db.DEFAULT_DB_PATH,
    upload_dir: str = DEFAULT_UPLOAD_DIR,
) -> int:
    """Calcula o hash, grava o arquivo recebido em disco e insere um novo
    registro `pendente` na fila (FR-005/FR-006/FR-007). Retorna o
    `envio_id`. Levanta TipoArquivoNaoSuportadoError para tipos não
    suportados — antes de gravar qualquer coisa em disco."""
    tipo = _tipo_arquivo(nome_original)
    hash_conteudo = calcular_hash_conteudo(conteudo)
    caminho, _ = salvar_arquivo_recebido(nome_original, conteudo, upload_dir=upload_dir)
    return storage_db.inserir_envio(caminho, tipo, hash_conteudo, db_path=db_path)


def reconciliar_fila_apos_reinicio(db_path: str = storage_db.DEFAULT_DB_PATH) -> int:
    """Reverte envios presos em `processando` para `pendente` ao iniciar o
    worker (research.md #11, Princípio VII) — retorna quantos foram
    revertidos."""
    return storage_db.reconciliar_processando_para_pendente(db_path=db_path)
