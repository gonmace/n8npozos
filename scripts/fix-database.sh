#!/bin/bash
# Script para solucionar problemas de conexión a la base de datos

set -e

echo "🔧 Solucionando problemas de conexión a la base de datos..."
echo ""

# Verificar que existe .env
if [ ! -f .env ]; then
    echo "❌ Error: Archivo .env no encontrado"
    exit 1
fi

source .env 2>/dev/null || true

echo "1️⃣ Verificando estado de contenedores..."
POSTGRES_CONTAINER=""
if docker ps | grep -q n8npozos-postgres; then
    POSTGRES_CONTAINER="n8npozos-postgres"
    echo "   ✅ PostgreSQL está corriendo (n8npozos-postgres)"
elif docker ps | grep -q postgres; then
    POSTGRES_CONTAINER="postgres"
    echo "   ✅ PostgreSQL está corriendo (postgres)"
else
    echo "   ⚠️  PostgreSQL no está corriendo. Iniciando..."
    docker compose --env-file .env -f deploy/docker-compose.yml up -d postgres
    echo "   ⏳ Esperando a que PostgreSQL esté listo..."
    sleep 10
    POSTGRES_CONTAINER="n8npozos-postgres"
fi

echo ""
echo "2️⃣ Verificando conexión a la base de datos..."
if [ -n "$POSTGRES_CONTAINER" ]; then
    if docker exec $POSTGRES_CONTAINER psql -U ${POSTGRES_USER:-magoreal} -d ${POSTGRES_DB:-pozos} -c "SELECT 1;" >/dev/null 2>&1; then
        echo "   ✅ Conexión exitosa"
    else
        echo "   ⚠️  Error de conexión. Verificando credenciales..."
        docker logs $POSTGRES_CONTAINER --tail 20 | grep -i error || echo "   Revisa los logs: docker logs $POSTGRES_CONTAINER"
    fi
else
    POSTGRES_CONTAINER="n8npozos-postgres"
fi

echo ""
echo "3️⃣ Verificando workflows..."
WORKFLOWS=$(docker exec $POSTGRES_CONTAINER psql -U ${POSTGRES_USER:-magoreal} -d ${POSTGRES_DB:-pozos} -t -c "SELECT COUNT(*) FROM workflow_entity;" 2>/dev/null | xargs)
if [ ! -z "$WORKFLOWS" ] && [ "$WORKFLOWS" != "0" ]; then
    echo "   ✅ Se encontraron $WORKFLOWS workflows"
else
    echo "   ⚠️  No se encontraron workflows en la base de datos actual"
fi

echo ""
echo "4️⃣ Reiniciando n8n para reconectar..."
docker compose --env-file .env -f deploy/docker-compose.yml restart n8n
sleep 5

echo ""
echo "5️⃣ Verificando estado de n8n..."
N8N_CONTAINER=""
if docker ps | grep -q n8npozos-n8n; then
    N8N_CONTAINER="n8npozos-n8n"
elif docker ps | grep -q n8n; then
    N8N_CONTAINER="n8n"
fi

if [ -n "$N8N_CONTAINER" ]; then
    if docker logs $N8N_CONTAINER --tail 10 2>&1 | grep -q "Database connection recovered\|Server started"; then
        echo "   ✅ n8n está conectado correctamente"
    else
        echo "   ⚠️  Revisa los logs: docker logs $N8N_CONTAINER"
    fi
else
    echo "   ⚠️  Contenedor n8n no encontrado"
fi

echo ""
echo "✅ Proceso completado"
echo ""
echo "💡 Accede a n8n en: http://localhost:5678"


