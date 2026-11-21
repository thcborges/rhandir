#!/usr/bin/env bash
# ==============================================================================
# Rhandir — Sincronização Obsidian Vault (data/vault) <-> Google Drive via rclone
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VAULT_DIR="${PROJECT_ROOT}/data/vault"
ENV_FILE="${PROJECT_ROOT}/.env"

# Carregar variáveis do .env se existir
if [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC1090
  export $(grep -E '^[A-Za-z_]+=' "$ENV_FILE" | xargs)
fi

REMOTE_TARGET="${RCLONE_VAULT_REMOTE:-gdrive:Obsidian}"
DIRECTION="${1:-pull}" # pull (padrão), push, ou bisync

mkdir -p "$VAULT_DIR"

echo "================================================================="
echo "🔄 Rhandir — Sincronização Obsidian Vault via rclone"
echo "  Direção:   ${DIRECTION^^}"
echo "  Local:     ${VAULT_DIR}"
echo "  Remoto:    ${REMOTE_TARGET}"
echo "================================================================="

case "$DIRECTION" in
  pull)
    echo "📥 Baixando alterações do Google Drive para o cofre local..."
    rclone sync "$REMOTE_TARGET" "$VAULT_DIR" \
      --fast-list \
      --drive-chunk-size 32M \
      --progress \
      -v
    ;;
  push)
    echo "📤 Enviando notas do cofre local para o Google Drive..."
    rclone sync "$VAULT_DIR" "$REMOTE_TARGET" \
      --fast-list \
      --drive-chunk-size 32M \
      --progress \
      -v
    ;;
  bisync)
    echo "🔄 Executando sincronização bidirecional..."
    rclone bisync "$VAULT_DIR" "$REMOTE_TARGET" \
      --resync \
      --verbose
    ;;
  *)
    echo "Uso: $0 [pull|push|bisync]"
    exit 1
    ;;
esac

echo "✅ Sincronização concluída com sucesso!"
