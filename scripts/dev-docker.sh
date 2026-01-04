#!/bin/bash
# Script para desarrollo CON Docker (comportamiento anterior)
# Usa este si prefieres desarrollo completamente containerizado

set -e

echo "🚀 Iniciando entorno de desarrollo CON Docker..."
echo ""
echo "💡 Para desarrollo local sin Docker, usa: ./scripts/dev-local.sh"
echo ""

# Verificar que existe .env
if [ ! -f .env ]; then
    echo "⚠️  Archivo .env no encontrado. Creando desde .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ Archivo .env creado. Por favor, edita las variables según tu entorno."
    else
        echo "❌ Error: No existe .env.example"
        exit 1
    fi
fi

# Detener y eliminar contenedores existentes si existen
echo "🧹 Limpiando contenedores existentes..."
docker-compose --env-file .env -f deploy/docker-compose.yml -f config/development/docker-compose.override.yml down 2>/dev/null || true

# Usar docker-compose con override de desarrollo
# --progress=plain muestra el output completo del build
# --env-file .env asegura que se lean las variables desde la raíz
echo "🔨 Construyendo imágenes..."
docker-compose --env-file .env -f deploy/docker-compose.yml -f config/development/docker-compose.override.yml build --progress=plain

echo "🚀 Iniciando servicios..."
docker-compose --env-file .env -f deploy/docker-compose.yml -f config/development/docker-compose.override.yml up

