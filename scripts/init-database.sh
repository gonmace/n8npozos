#!/bin/bash
# Script para inicializar la base de datos de n8n si no existe

set -e

echo "🔧 Inicializando base de datos de n8n..."

# Cargar variables de entorno desde .env si existe
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Valores por defecto
POSTGRES_USER=${POSTGRES_USER:-magoreal}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-changeme}
POSTGRES_DB=${POSTGRES_DB:-pozos}
POSTGRES_CONTAINER="n8npozos-postgres"

# Verificar que el contenedor de PostgreSQL esté corriendo
if ! docker ps | grep -q "$POSTGRES_CONTAINER"; then
    echo "❌ Error: Contenedor $POSTGRES_CONTAINER no está corriendo"
    echo "   Inicia PostgreSQL primero con: docker compose --env-file .env -f deploy/docker-compose.yml up -d postgres"
    exit 1
fi

echo "✅ Contenedor PostgreSQL está corriendo"

# Esperar a que PostgreSQL esté listo
echo "⏳ Esperando a que PostgreSQL esté listo..."
for i in {1..30}; do
    if docker exec $POSTGRES_CONTAINER pg_isready -U $POSTGRES_USER >/dev/null 2>&1; then
        echo "✅ PostgreSQL está listo"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Error: PostgreSQL no está respondiendo después de 30 intentos"
        exit 1
    fi
    sleep 1
done

# Verificar si la base de datos existe
echo "🔍 Verificando si la base de datos '$POSTGRES_DB' existe..."
# Usar PGPASSWORD para evitar problemas de autenticación
export PGPASSWORD=$POSTGRES_PASSWORD
DB_EXISTS=$(docker exec -e PGPASSWORD=$POSTGRES_PASSWORD $POSTGRES_CONTAINER psql -U $POSTGRES_USER -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$POSTGRES_DB'" 2>/dev/null || echo "")

if [ -z "$DB_EXISTS" ] || [ "$DB_EXISTS" != "1" ]; then
    echo "📦 Creando base de datos '$POSTGRES_DB'..."
    docker exec -e PGPASSWORD=$POSTGRES_PASSWORD $POSTGRES_CONTAINER psql -U $POSTGRES_USER -d postgres -c "CREATE DATABASE \"$POSTGRES_DB\";"
    if [ $? -eq 0 ]; then
        echo "✅ Base de datos '$POSTGRES_DB' creada exitosamente"
    else
        echo "❌ Error al crear la base de datos '$POSTGRES_DB'"
        exit 1
    fi
else
    echo "✅ La base de datos '$POSTGRES_DB' ya existe"
fi

# Verificar que la base de datos es accesible
echo "🔍 Verificando acceso a la base de datos..."
if docker exec -e PGPASSWORD=$POSTGRES_PASSWORD $POSTGRES_CONTAINER psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT 1;" >/dev/null 2>&1; then
    echo "✅ Acceso a la base de datos verificado"
else
    echo "❌ Error: No se puede acceder a la base de datos '$POSTGRES_DB'"
    echo "   Verifica que POSTGRES_USER y POSTGRES_PASSWORD sean correctos en .env"
    exit 1
fi

echo ""
echo "✅ Base de datos inicializada correctamente"
echo "🚀 Ahora puedes iniciar n8n con:"
echo "   docker compose --env-file .env -f deploy/docker-compose.yml up -d n8n"
echo "   O simplemente: make prod"
