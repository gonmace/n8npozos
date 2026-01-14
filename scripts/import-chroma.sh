#!/bin/bash
# Script para importar el volumen de ChromaDB en el VPS
# Uso: ./scripts/import-chroma.sh [ruta_backup.tar.gz]

set -e

if [ -z "$1" ]; then
    echo "❌ Error: Debes especificar la ruta del archivo de backup"
    echo "   Uso: ./scripts/import-chroma.sh /ruta/al/backup/chroma_YYYYMMDD_HHMMSS.tar.gz"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Error: Archivo de backup no encontrado: $BACKUP_FILE"
    exit 1
fi

echo "📦 Importando volumen de ChromaDB desde: $BACKUP_FILE"

# Verificar que ChromaDB no esté corriendo
if docker ps | grep -q chroma; then
    echo "🛑 Deteniendo contenedor ChromaDB..."
    docker stop chroma
fi

# Eliminar contenedor si existe
if docker ps -a | grep -q chroma; then
    echo "🗑️  Eliminando contenedor ChromaDB..."
    docker rm chroma 2>/dev/null || true
fi

# Eliminar volumen existente si existe (¡CUIDADO! Esto borra datos existentes)
if docker volume ls | grep -q chroma_storage; then
    echo "⚠️  ADVERTENCIA: El volumen chroma_storage ya existe."
    echo "   Esto sobrescribirá los datos existentes."
    read -p "   ¿Continuar? (s/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        echo "❌ Operación cancelada"
        exit 1
    fi
    echo "🗑️  Eliminando volumen existente..."
    docker volume rm chroma_storage
fi

# Crear nuevo volumen
echo "📦 Creando nuevo volumen chroma_storage..."
docker volume create chroma_storage

# Restaurar datos desde el backup
echo "📥 Restaurando datos desde backup..."
docker run --rm \
    -v chroma_storage:/data \
    -v "$(pwd)/$(dirname "$BACKUP_FILE")":/backup:ro \
    alpine sh -c "cd /data && tar xzf /backup/$(basename "$BACKUP_FILE")"

echo "✅ Datos de ChromaDB restaurados exitosamente"
echo ""
echo "🚀 Ahora puedes iniciar los servicios con:"
echo "   make prod"
echo "   O"
echo "   docker-compose --env-file .env -f deploy/docker-compose.yml up -d chroma"
