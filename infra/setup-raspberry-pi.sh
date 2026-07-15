#!/usr/bin/env bash
# Provisiona o Raspberry Pi para rodar o servidor financiALL (feature 001).
# Idempotente: seguro rodar mais de uma vez. Verifica o que a imagem padrao
# do Raspberry Pi OS ja traz antes de instalar (research.md #14).
#
# Uso: ./setup-raspberry-pi.sh [caminho-do-repo]
# Requer sudo sem senha (ou sera solicitada a senha pelo proprio sudo).

set -euo pipefail

REPO_DIR="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
VENV_DIR="$REPO_DIR/.venv"

echo "==> financiALL: provisionando em $REPO_DIR"

echo "--> Atualizando indice de pacotes"
sudo apt-get update -y

# tesseract-ocr, o pacote de idioma portugues e libzbar0 (leitura de QR
# Code via pyzbar) nao vem na imagem padrao.
echo "--> Garantindo tesseract-ocr, tesseract-ocr-por, libzbar0, python3-venv"
sudo apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-por \
    libzbar0 \
    python3-venv \
    python3-pip

# poppler-utils (pdftoppm) e zram (systemd-zram-generator) ja vem na imagem
# padrao do Raspberry Pi OS usada neste projeto; instala apenas se faltar,
# sem forcar reinstalacao do que ja existe.
if ! command -v pdftoppm >/dev/null 2>&1; then
    echo "--> pdftoppm ausente, instalando poppler-utils"
    sudo apt-get install -y --no-install-recommends poppler-utils
else
    echo "--> poppler-utils ja presente ($(command -v pdftoppm)), pulando"
fi

if systemctl is-active --quiet systemd-zram-setup@zram0.service 2>/dev/null; then
    echo "--> zram ja ativo (systemd-zram-setup@zram0.service), pulando"
elif ! dpkg -l | grep -qi zram-tools 2>/dev/null; then
    echo "--> zram ausente, instalando zram-tools como rede de seguranca"
    sudo apt-get install -y --no-install-recommends zram-tools
else
    echo "--> zram-tools ja instalado, pulando"
fi

echo "--> Criando ambiente virtual Python em $VENV_DIR (se ainda nao existir)"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

echo "--> Instalando dependencias do projeto no venv"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -e "$REPO_DIR"

echo "--> Criando diretorio de dados (banco SQLite + uploads)"
mkdir -p "$REPO_DIR/data/uploads"

# Caddy (feature 007) -- proxy reverso HTTPS local, certificado autoassinado
# gerado pelo proprio Caddy (Caddyfile usa `tls internal`), necessario para
# a API de camera do navegador (getUserMedia exige contexto seguro). Prefere
# o pacote ja disponivel no repositorio oficial da distro (Debian 13/trixie
# ja empacota Caddy) -- so usa o repositorio proprio do Caddy (Cloudsmith)
# como alternativa se o pacote nao existir no repositorio ja configurado.
if command -v caddy >/dev/null 2>&1; then
    echo "--> Caddy ja instalado ($(command -v caddy)), pulando instalacao"
elif apt-cache show caddy >/dev/null 2>&1; then
    echo "--> Instalando Caddy do repositorio ja configurado da distro"
    sudo apt-get install -y --no-install-recommends caddy
else
    echo "--> Caddy ausente do repositorio da distro, usando repositorio oficial do Caddy"
    sudo apt-get install -y --no-install-recommends debian-keyring debian-archive-keyring apt-transport-https curl
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
        | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
        | sudo tee /etc/apt/sources.list.d/caddy-stable.list
    sudo apt-get update -y
    sudo apt-get install -y --no-install-recommends caddy
fi

echo "--> Instalando infra/Caddyfile em /etc/caddy/Caddyfile"
sudo cp "$REPO_DIR/infra/Caddyfile" /etc/caddy/Caddyfile
sudo systemctl reload caddy 2>/dev/null || sudo systemctl restart caddy

echo "==> Provisionamento concluido."
echo "    Proximo passo: instalar o servico systemd com"
echo "    sudo cp \"$REPO_DIR/infra/financiall.service\" /etc/systemd/system/ && \\"
echo "    sudo systemctl daemon-reload && sudo systemctl enable --now financiall"
echo "    financiALL fica acessivel via HTTPS em https://finall.local:5443 (producao)"
echo "    e https://finall.local:5444 (dev) depois do Caddy recarregar."
