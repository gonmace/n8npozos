#!/bin/bash
# Sube los datos de n8n y ChromaDB a un servidor remoto via rsync
#
# Uso:
#   ./scripts/upload-data.sh user@servidor
#   ./scripts/upload-data.sh user@servidor --all        # incluye postgres
#   ./scripts/upload-data.sh user@servidor --dry-run    # simular sin copiar

set -e

REMOTE="${1}"
REMOTE_DIR="~/n8n/n8npozos"
EXTRA_FLAGS=""
INCLUDE_POSTGRES=false

if [ -z "$REMOTE" ]; then
    echo "❌ Uso: $0 user@servidor [--all] [--dry-run]"
    echo "   Ejemplo: $0 gonzalo@vmi551715"
    exit 1
fi

shift
for arg in "$@"; do
    case "$arg" in
        --all)      INCLUDE_POSTGRES=true ;;
        --dry-run)  EXTRA_FLAGS="--dry-run" ; echo "ℹ️  Modo simulación — no se copiará nada" ;;
    esac
done

echo "🚀 Destino: ${REMOTE}:${REMOTE_DIR}"
echo ""

upload() {
    local DIR="$1"
    local LABEL="$2"
    if [ -d "./$DIR" ] && [ "$(ls -A ./$DIR 2>/dev/null | grep -v .gitkeep)" ]; then
        echo "📤 Subiendo $LABEL..."
        rsync -avz --progress $EXTRA_FLAGS "./$DIR/" "${REMOTE}:${REMOTE_DIR}/${DIR}/"
        echo "   ✅ $LABEL listo"
    else
        echo "   ⚠️  $DIR vacío o no existe — omitido"
    fi
    echo ""
}

upload "n8n_storage"    "n8n"
upload "chroma_storage" "ChromaDB"

if [ "$INCLUDE_POSTGRES" = true ]; then
    upload "postgres_storage" "PostgreSQL"
fi

echo "✅ Transferencia completada"
echo ""
echo "⚠️  Recordá que N8N_ENCRYPTION_KEY en el servidor destino debe ser"
echo "   exactamente igual a la del origen, o las credenciales de n8n no funcionarán."
