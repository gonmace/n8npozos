#!/bin/bash
# Script para detener servicios

set -e

ENV=${1:-development}

if [ "$ENV" = "production" ]; then
    echo "🛑 Deteniendo servicios de producción..."
    docker compose --env-file .env -f deploy/docker-compose.yml -f config/production/docker-compose.override.yml down
else
    echo "🛑 Deteniendo servicios de desarrollo..."
    docker compose --env-file .env -f deploy/docker-compose.yml -f config/development/docker-compose.override.yml down
fi

echo "✅ Servicios detenidos"

