#!/bin/bash
# Script para exportar el volumen de ChromaDB desde el servidor local
# Uso: ./scripts/export-chroma.sh [ruta_destino]

set -e

BACKUP_DIR="${1:-./chroma-backup}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/chroma_${TIMESTAMP}.tar.gz"

mkdir -p "$BACKUP_DIR"

echo "📦 Exportando volumen de ChromaDB..."

# Verificar que el volumen existe
if ! docker volume ls | grep -q chroma_storage; then
    echo "❌ Error: Volumen chroma_storage no encontrado"
    echo "   Asegúrate de que ChromaDB haya sido ejecutado al menos una vez"
    exit 1
fi

# Detener ChromaDB si está corriendo para asegurar consistencia
echo "🛑 Deteniendo contenedor ChromaDB (si está corriendo)..."
docker stop chroma 2>/dev/null || true

# Crear backup del volumen
echo "💾 Creando backup del volumen chroma_storage..."
docker run --rm \
    -v chroma_storage:/data:ro \
    -v "$(pwd)/$BACKUP_DIR":/backup \
    alpine tar czf /backup/chroma_${TIMESTAMP}.tar.gz -C /data .

# Reiniciar ChromaDB si estaba corriendo
if docker ps -a | grep -q chroma; then
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
