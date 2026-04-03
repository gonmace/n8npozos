#!/bin/bash
# Restaura datos desde backups/ a los directorios bind mount

set -e

BACKUP_DIR="./backups"

if [ ! -d "$BACKUP_DIR" ]; then
    echo "❌ Error: Directorio $BACKUP_DIR no encontrado."
    echo "   Copia los archivos de backup primero:"
    echo "   scp usuario@origen:~/n8npozos/backups/*.tar.gz ./backups/"
    exit 1
fi

echo "🔄 Restaurando datos desde $BACKUP_DIR..."

# Restaurar n8n
if [ -f "$BACKUP_DIR/n8n_storage.tar.gz" ]; then
    echo "📦 Restaurando n8n..."
    mkdir -p ./n8n_storage
    tar xzf "$BACKUP_DIR/n8n_storage.tar.gz" -C .
    echo "   ✅ n8n restaurado en ./n8n_storage"
else
    echo "   ⚠️  No se encontró backups/n8n_storage.tar.gz — omitiendo"
fi

# Restaurar PostgreSQL
if [ -f "$BACKUP_DIR/postgres_storage.tar.gz" ]; then
    echo "📦 Restaurando PostgreSQL..."
    mkdir -p ./postgres_storage
    tar xzf "$BACKUP_DIR/postgres_storage.tar.gz" -C .
    # PostgreSQL corre como uid 999 — ajustar permisos
    docker run --rm -v "$(pwd)/postgres_storage:/data" alpine chown -R 999:999 /data
    echo "   ✅ PostgreSQL restaurado en ./postgres_storage"
else
    echo "   ⚠️  No se encontró backups/postgres_storage.tar.gz — omitiendo"
fi

# Restaurar ChromaDB
if [ -f "$BACKUP_DIR/chroma_storage.tar.gz" ]; then
    echo "📦 Restaurando ChromaDB..."
    mkdir -p ./chroma_storage
    tar xzf "$BACKUP_DIR/chroma_storage.tar.gz" -C .
    echo "   ✅ ChromaDB restaurado en ./chroma_storage"
else
    echo "   ⚠️  No se encontró backups/chroma_storage.tar.gz — omitiendo"
fi

echo ""
echo "✅ Restauración completa."
echo "   Ejecutá 'make prod' para levantar los servicios."
