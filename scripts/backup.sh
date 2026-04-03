#!/bin/bash
# Script para hacer backup de datos del proyecto

set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

echo "💾 Creando backup..."

# Backup de PostgreSQL (bind mount)
if [ -d "./postgres_storage" ] && [ "$(ls -A ./postgres_storage 2>/dev/null | grep -v .gitkeep)" ]; then
    echo "📦 Respaldando PostgreSQL..."
    tar czf "${BACKUP_DIR}/postgres_${TIMESTAMP}.tar.gz" -C . postgres_storage
    echo "   ✅ postgres_${TIMESTAMP}.tar.gz"
fi

# Backup de n8n (bind mount)
if [ -d "./n8n_storage" ] && [ "$(ls -A ./n8n_storage 2>/dev/null | grep -v .gitkeep)" ]; then
    echo "📦 Respaldando n8n..."
    tar czf "${BACKUP_DIR}/n8n_${TIMESTAMP}.tar.gz" -C . n8n_storage
    echo "   ✅ n8n_${TIMESTAMP}.tar.gz"
fi

# Backup de ChromaDB (bind mount)
if [ -d "./chroma_storage" ] && [ "$(ls -A ./chroma_storage 2>/dev/null | grep -v .gitkeep)" ]; then
    echo "📦 Respaldando ChromaDB..."
    tar czf "${BACKUP_DIR}/chroma_${TIMESTAMP}.tar.gz" -C . chroma_storage
    echo "   ✅ chroma_${TIMESTAMP}.tar.gz"
fi

echo ""
echo "✅ Backup completado en $BACKUP_DIR"
