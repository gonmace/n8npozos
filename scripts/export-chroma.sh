#!/bin/bash
# Script para exportar el volumen de ChromaDB desde el servidor local
# Uso: ./scripts/export-chroma.sh [ruta_destino]

set -e

BACKUP_DIR="${1:-./chroma-backup}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/chroma_${TIMESTAMP}.tar.gz"

mkdir -p "$BACKUP_DIR"

echo "📦 Exportando volumen de ChromaDB..."

# Buscar el volumen de ChromaDB (puede tener diferentes nombres según el proyecto)
VOLUME_NAME=""

# Primero buscar volúmenes con "chroma" en el nombre (más flexible)
CHROMA_VOLUMES=$(docker volume ls | grep -i chroma | awk '{print $2}')
if [ -n "$CHROMA_VOLUMES" ]; then
    # Si hay múltiples, preferir chroma_storage, sino tomar el primero
    if echo "$CHROMA_VOLUMES" | grep -q "^chroma_storage$"; then
        VOLUME_NAME="chroma_storage"
    else
        VOLUME_NAME=$(echo "$CHROMA_VOLUMES" | head -1)
        echo "⚠️  Usando volumen encontrado: $VOLUME_NAME"
    fi
fi

# Si no se encontró ningún volumen de ChromaDB
if [ -z "$VOLUME_NAME" ]; then
    echo "📋 Volúmenes disponibles:"
    docker volume ls
    echo ""
    echo "❌ Error: Volumen de ChromaDB no encontrado"
    echo ""
    echo "💡 Opciones:"
    echo "   1. Si ChromaDB está corriendo con docker compose, ejecuta primero:"
    echo "      docker compose --env-file .env -f deploy/docker-compose.yml up -d chroma"
    echo ""
    echo "   2. Si los datos están en otro lugar, especifica el nombre del volumen:"
    echo "      docker volume ls  # para ver los volúmenes disponibles"
    echo ""
    echo "   3. Si ChromaDB está en el VPS, ejecuta este script en el VPS, no aquí"
    exit 1
fi

# Detener ChromaDB si está corriendo para asegurar consistencia
echo "🛑 Deteniendo contenedor ChromaDB (si está corriendo)..."
docker stop n8npozos-chroma 2>/dev/null || docker stop chroma 2>/dev/null || true

# Crear backup del volumen
echo "💾 Creando backup del volumen $VOLUME_NAME..."
docker run --rm \
    -v ${VOLUME_NAME}:/data:ro \
    -v "$(pwd)/$BACKUP_DIR":/backup \
    alpine tar czf /backup/chroma_${TIMESTAMP}.tar.gz -C /data .

# Reiniciar ChromaDB si estaba corriendo
if docker ps -a | grep -q n8npozos-chroma; then
    echo "🔄 Reiniciando ChromaDB..."
    docker start n8npozos-chroma 2>/dev/null || true
elif docker ps -a | grep -q chroma; then
    echo "🔄 Reiniciando ChromaDB..."
    docker start chroma 2>/dev/null || true
fi

echo "✅ Backup creado: $BACKUP_FILE"
echo "📊 Tamaño: $(du -h "$BACKUP_FILE" | cut -f1)"
echo ""
echo "📤 Para transferir al VPS, puedes usar:"
echo "   scp $BACKUP_FILE usuario@vps:/ruta/destino/"
echo "   O usar rsync para transferencia más eficiente:"
echo "   rsync -avz --progress $BACKUP_FILE usuario@vps:/ruta/destino/"
