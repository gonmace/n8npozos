#!/bin/bash
# Script para inicializar el directorio de ChromaDB
# Se ejecuta automáticamente en los scripts de despliegue

set -e

CHROMA_DIR="deploy/chroma_storage"

echo "📁 Inicializando directorio de ChromaDB..."

# Crear directorio si no existe
if [ ! -d "$CHROMA_DIR" ]; then
    echo "   Creando directorio: $CHROMA_DIR"
    mkdir -p "$CHROMA_DIR"
fi

# Crear .gitkeep si no existe (para mantener el directorio en git)
if [ ! -f "$CHROMA_DIR/.gitkeep" ]; then
    echo "   Creando .gitkeep"
    touch "$CHROMA_DIR/.gitkeep"
fi

# Asegurar permisos correctos
chmod 755 "$CHROMA_DIR"

echo "✅ Directorio de ChromaDB listo: $CHROMA_DIR"
