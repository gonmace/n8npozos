#!/bin/bash
# Script para iniciar solo los servicios necesarios (PostgreSQL, ChromaDB, n8n) en Docker
# Útil para desarrollo local donde ejecutas la app sin Docker

set -e

echo "🚀 Iniciando servicios de soporte (PostgreSQL, ChromaDB, n8n)..."
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

# Iniciar PostgreSQL, ChromaDB y n8n
docker-compose --env-file .env -f deploy/docker-compose.yml up -d postgres chroma n8n

echo ""
echo "✅ Servicios iniciados:"
echo "   - PostgreSQL: localhost:5432"
echo "   - ChromaDB: localhost:8000"
echo "   - n8n: http://localhost:5678"
echo ""
echo "💡 Para detener los servicios:"
echo "   docker-compose --env-file .env -f deploy/docker-compose.yml stop postgres chroma n8n"
echo ""
echo "💡 Para ver logs:"
echo "   docker-compose --env-file .env -f deploy/docker-compose.yml logs -f"

