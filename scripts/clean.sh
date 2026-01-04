#!/bin/bash
# Script para limpiar contenedores, imágenes y volúmenes

set -e

echo "🧹 Limpiando contenedores, imágenes y volúmenes..."

read -p "¿Estás seguro? Esto eliminará todos los contenedores, imágenes y volúmenes. (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Operación cancelada."
    exit 1
fi

docker-compose --env-file .env -f deploy/docker-compose.yml down -v --rmi all
docker system prune -f

echo "✅ Limpieza completada"

