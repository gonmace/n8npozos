#!/bin/bash
# Script para producción

set -e

echo "🚀 Iniciando entorno de producción..."

# Verificar que existe .env
if [ ! -f .env ]; then
    echo "❌ Error: Archivo .env no encontrado. Es requerido para producción."
    exit 1
fi

# Detener y eliminar contenedores existentes si existen
echo "🧹 Limpiando contenedores existentes..."
docker compose --env-file .env -f deploy/docker-compose.yml -f config/production/docker-compose.override.yml down 2>/dev/null || true

# Construir y levantar servicios
# --progress=plain muestra el output completo del build
# --env-file .env asegura que se lean las variables desde la raíz
echo "🔨 Construyendo imágenes..."
docker compose --env-file .env -f deploy/docker-compose.yml -f config/production/docker-compose.override.yml build --progress=plain

echo "🚀 Iniciando servicios..."
docker compose --env-file .env -f deploy/docker-compose.yml -f config/production/docker-compose.override.yml up -d

echo "✅ Servicios iniciados en modo producción"
echo "📊 Ver logs con: docker compose -f deploy/docker-compose.yml logs -f"

