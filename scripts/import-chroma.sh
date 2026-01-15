#!/bin/bash
# Script para importar ChromaDB en el VPS
# Ahora usa bind mount (directorio) en lugar de volumen Docker
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

echo "📦 Importando ChromaDB desde: $BACKUP_FILE"

# Determinar el directorio de destino
CHROMA_DIR="./chroma_storage"
if [ -d "./deploy/chroma_storage" ]; then
    CHROMA_DIR="./deploy/chroma_storage"
fi

# Verificar que ChromaDB no esté corriendo
if docker ps | grep -q n8npozos-chroma; then
    echo "🛑 Deteniendo contenedor ChromaDB..."
    docker stop n8npozos-chroma
elif docker ps | grep -q chroma; then
    echo "🛑 Deteniendo contenedor ChromaDB..."
    docker stop chroma
fi

# Eliminar contenedor si existe
if docker ps -a | grep -q n8npozos-chroma; then
    echo "🗑️  Eliminando contenedor ChromaDB..."
    docker rm n8npozos-chroma 2>/dev/null || true
elif docker ps -a | grep -q chroma; then
    echo "🗑️  Eliminando contenedor ChromaDB..."
    docker rm chroma 2>/dev/null || true
fi

# Verificar si el directorio ya existe
if [ -d "$CHROMA_DIR" ] && [ "$(ls -A $CHROMA_DIR 2>/dev/null)" ]; then
    echo "⚠️  ADVERTENCIA: El directorio $CHROMA_DIR ya existe y contiene datos."
    echo "   Esto sobrescribirá los datos existentes."
    read -p "   ¿Continuar? (s/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        echo "❌ Operación cancelada"
        exit 1
    fi
    echo "🗑️  Eliminando directorio existente..."
    rm -rf "$CHROMA_DIR"
fi

# Crear directorio de destino
echo "📦 Creando directorio de destino: $CHROMA_DIR"
mkdir -p "$(dirname "$CHROMA_DIR")"

# Restaurar datos desde el backup
echo "📥 Restaurando datos desde backup..."
tar xzf "$BACKUP_FILE" -C "$(dirname "$CHROMA_DIR")"

# Verificar que se restauró correctamente
if [ -d "$CHROMA_DIR" ]; then
    echo "✅ Datos de ChromaDB restaurados exitosamente en $CHROMA_DIR"
    echo "📊 Tamaño: $(du -sh "$CHROMA_DIR" | cut -f1)"
else
    echo "❌ Error: No se pudo restaurar el directorio"
    exit 1
fi

echo ""
echo "🚀 Ahora puedes iniciar los servicios con:"
echo "   make prod"
echo "   O"
echo "   docker compose --env-file .env -f deploy/docker-compose.yml up -d chroma"
