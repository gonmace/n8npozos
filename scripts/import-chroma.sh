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

# Buscar y eliminar volúmenes de ChromaDB existentes (¡CUIDADO! Esto borra datos existentes)
CHROMA_VOLUMES=$(docker volume ls | grep -i chroma | awk '{print $2}')
if [ -n "$CHROMA_VOLUMES" ]; then
    echo "⚠️  ADVERTENCIA: Se encontraron volúmenes de ChromaDB existentes:"
    echo "$CHROMA_VOLUMES" | sed 's/^/   - /'
    echo "   Esto sobrescribirá los datos existentes."
    read -p "   ¿Continuar? (s/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        echo "❌ Operación cancelada"
        exit 1
    fi
    echo "🗑️  Eliminando volúmenes existentes..."
    echo "$CHROMA_VOLUMES" | while read vol; do
        docker volume rm "$vol" 2>/dev/null || true
    done
fi

# Determinar el nombre del volumen a crear (usar el mismo que está en docker-compose.yml)
# Por defecto es chroma_storage, pero puede ser deploy_chroma_storage si se usa con prefijo
VOLUME_NAME="chroma_storage"
if docker compose --env-file .env -f deploy/docker-compose.yml config 2>/dev/null | grep -q "deploy_chroma_storage"; then
    VOLUME_NAME="deploy_chroma_storage"
fi

# Crear nuevo volumen
echo "📦 Creando nuevo volumen $VOLUME_NAME..."
docker volume create "$VOLUME_NAME"

# Restaurar datos desde el backup
echo "📥 Restaurando datos desde backup..."
docker run --rm \
    -v ${VOLUME_NAME}:/data \
    -v "$(pwd)/$(dirname "$BACKUP_FILE")":/backup:ro \
    alpine sh -c "cd /data && tar xzf /backup/$(basename "$BACKUP_FILE")"

echo "✅ Datos de ChromaDB restaurados exitosamente"
echo ""
echo "🚀 Ahora puedes iniciar los servicios con:"
echo "   make prod"
echo "   O"
echo "   docker compose --env-file .env -f deploy/docker-compose.yml up -d chroma"
