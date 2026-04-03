#!/bin/bash
# Verifica y crea las bases de datos necesarias si no existen.
# Úsalo cuando postgres_storage ya tiene datos (el init script no corre en ese caso).

set -e

if [ -f .env ]; then
    set -a; source .env; set +a
fi

POSTGRES_USER=${POSTGRES_USER:-magoreal}
POSTGRES_CONTAINER="n8npozos-postgres"

if ! docker ps | grep -q "$POSTGRES_CONTAINER"; then
    echo "❌ Error: Contenedor $POSTGRES_CONTAINER no está corriendo"
    exit 1
fi

echo "⏳ Esperando a que PostgreSQL esté listo..."
for i in {1..30}; do
    if docker exec $POSTGRES_CONTAINER pg_isready -U $POSTGRES_USER >/dev/null 2>&1; then
        echo "✅ PostgreSQL listo"
        break
    fi
    [ $i -eq 30 ] && echo "❌ PostgreSQL no responde" && exit 1
    sleep 1
done

for DB in n8n n8n_django; do
    EXISTS=$(docker exec $POSTGRES_CONTAINER psql -U $POSTGRES_USER -tAc \
        "SELECT 1 FROM pg_database WHERE datname='$DB'" postgres 2>/dev/null || echo "")
    if [ "$EXISTS" != "1" ]; then
        echo "📦 Creando base de datos '$DB'..."
        docker exec $POSTGRES_CONTAINER psql -U $POSTGRES_USER -c \
            "CREATE DATABASE \"$DB\";" postgres
        echo "   ✅ '$DB' creada"
    else
        echo "   ✅ '$DB' ya existe"
    fi
done

echo ""
echo "✅ Bases de datos listas."
