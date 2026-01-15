#!/bin/bash
# Script para exportar ChromaDB desde el servidor local
# Ahora usa bind mount (directorio) en lugar de volumen Docker
# Uso: ./scripts/export-chroma.sh [ruta_destino]

set -e

BACKUP_DIR="${1:-./chroma-backup}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/chroma_${TIMESTAMP}.tar.gz"

mkdir -p "$BACKUP_DIR"

echo "📦 Exportando ChromaDB..."

# Buscar el directorio de ChromaDB
CHROMA_DIR=""
if [ -d "./chroma_storage" ]; then
    CHROMA_DIR="./chroma_storage"
elif [ -d "./deploy/chroma_storage" ]; then
    CHROMA_DIR="./deploy/chroma_storage"
elif [ -d "../chroma_storage" ]; then
    CHROMA_DIR="../chroma_storage"
else
    echo "❌ Error: Directorio de ChromaDB no encontrado"
    echo ""
    echo "💡 Buscando directorios chroma_storage..."
    find . -type d -name "chroma_storage" 2>/dev/null | head -5
    echo ""
    echo "   Si ChromaDB está usando un volumen Docker, primero migra a bind mount:"
    echo "   1. Detén ChromaDB: docker stop n8npozos-chroma"
    echo "   2. Copia el volumen a un directorio:"
    echo "      docker run --rm -v chroma_storage:/data -v \$(pwd):/backup alpine tar czf /backup/chroma_storage.tar.gz -C /data ."
    echo "   3. Extrae: mkdir -p chroma_storage && tar xzf chroma_storage.tar.gz -C chroma_storage"
    exit 1
fi

# Verificar que el directorio no esté vacío
if [ ! "$(ls -A $CHROMA_DIR 2>/dev/null)" ]; then
    echo "⚠️  Advertencia: El directorio $CHROMA_DIR está vacío"
    echo "   ¿ChromaDB se ha inicializado correctamente?"
fi

# Detener ChromaDB si está corriendo para asegurar consistencia
echo "🛑 Deteniendo contenedor ChromaDB (si está corriendo)..."
docker stop n8npozos-chroma 2>/dev/null || docker stop chroma 2>/dev/null || true

# Crear backup del directorio
echo "💾 Creando backup del directorio $CHROMA_DIR..."
tar czf "$BACKUP_FILE" -C "$(dirname "$CHROMA_DIR")" "$(basename "$CHROMA_DIR")"

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
echo "   scp $BACKUP_FILE magoreal@vmi2527689.contaboserver.net:~/n8n_pozos/chroma-backup/"
echo "   O usar rsync para transferencia más eficiente:"
echo "   rsync -avz --progress $BACKUP_FILE magoreal@vmi2527689.contaboserver.net:~/n8n_pozos/chroma-backup/"
