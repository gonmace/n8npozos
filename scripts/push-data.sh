#!/bin/bash
# Empaqueta n8n y ChromaDB, los commitea y pushea al repo.
# En el servidor: make prod (git pull) + make restore

set -e

BACKUP_DIR="./backups"
mkdir -p "$BACKUP_DIR"

echo "💾 Empaquetando datos..."

pack() {
    local DIR="$1"
    local LABEL="$2"
    local OUT="${BACKUP_DIR}/${DIR}.tar.gz"

    if [ -d "./$DIR" ] && [ "$(ls -A ./$DIR 2>/dev/null | grep -v .gitkeep)" ]; then
        echo "📦 Empaquetando $LABEL..."
        tar czf "$OUT" -C . "$DIR"
        echo "   ✅ ${DIR}.tar.gz ($(du -sh "$OUT" | cut -f1))"
    else
        echo "   ⚠️  $DIR vacío — omitido"
    fi
}

pack "n8n_storage"    "n8n"
pack "chroma_storage" "ChromaDB"

echo ""
echo "📤 Commiteando y pusheando..."

git add -f backups/n8n_storage.tar.gz backups/chroma_storage.tar.gz 2>/dev/null || true
git commit -m "chore: update data backups (n8n + chroma)"
git push

echo ""
echo "✅ Listo. En el servidor ejecutá:"
echo "   make prod    # git pull + build + up"
echo "   make restore # restaurar datos"
echo ""
echo "⚠️  Recordá que N8N_ENCRYPTION_KEY debe ser igual en origen y destino."
