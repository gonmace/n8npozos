#!/bin/bash
# Script para hacer backup de volúmenes de Docker

set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

echo "💾 Creando backup de volúmenes..."

# Backup de PostgreSQL
if docker volume ls | grep -q postgres_storage; then
    echo "📦 Respaldando PostgreSQL..."
    docker run --rm \
        -v postgres_storage:/data \
        -v "$(pwd)/$BACKUP_DIR":/backup \
        alpine tar czf /backup/postgres_${TIMESTAMP}.tar.gz -C /data .
fi

# Backup de n8n
if docker volume ls | grep -q n8n_storage; then
    echo "📦 Respaldando n8n..."
    docker run --rm \
        -v n8n_storage:/data \
        -v "$(pwd)/$BACKUP_DIR":/backup \
        alpine tar czf /backup/n8n_${TIMESTAMP}.tar.gz -C /data .
fi

# Backup de ChromaDB
if docker volume ls | grep -q chroma_storage; then
    echo "📦 Respaldando ChromaDB..."
    docker run --rm \
        -v chroma_storage:/data \
        -v "$(pwd)/$BACKUP_DIR":/backup \
        alpine tar czf /backup/chroma_${TIMESTAMP}.tar.gz -C /data .
fi

echo "✅ Backup completado en $BACKUP_DIR"


