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
if ! docker ps | grep -q postgres; then
    echo "   ⚠️  PostgreSQL no está corriendo. Iniciando..."
    docker-compose --env-file .env -f deploy/docker-compose.yml up -d postgres
    echo "   ⏳ Esperando a que PostgreSQL esté listo..."
    sleep 10
else
    echo "   ✅ PostgreSQL está corriendo"
fi

echo ""
echo "2️⃣ Verificando conexión a la base de datos..."
if docker exec postgres psql -U ${POSTGRES_USER:-magoreal} -d ${POSTGRES_DB:-n8n} -c "SELECT 1;" >/dev/null 2>&1; then
    echo "   ✅ Conexión exitosa"
else
    echo "   ⚠️  Error de conexión. Verificando credenciales..."
    docker logs postgres --tail 20 | grep -i error || echo "   Revisa los logs: docker logs postgres"
fi

echo ""
echo "3️⃣ Verificando workflows..."
WORKFLOWS=$(docker exec postgres psql -U ${POSTGRES_USER:-magoreal} -d ${POSTGRES_DB:-n8n} -t -c "SELECT COUNT(*) FROM workflow_entity;" 2>/dev/null | xargs)
if [ ! -z "$WORKFLOWS" ] && [ "$WORKFLOWS" != "0" ]; then
    echo "   ✅ Se encontraron $WORKFLOWS workflows"
else
    echo "   ⚠️  No se encontraron workflows en la base de datos actual"
fi

echo ""
echo "4️⃣ Reiniciando n8n para reconectar..."
docker-compose --env-file .env -f deploy/docker-compose.yml restart n8n
sleep 5

echo ""
echo "5️⃣ Verificando estado de n8n..."
if docker logs n8n --tail 10 2>&1 | grep -q "Database connection recovered\|Server started"; then
    echo "   ✅ n8n está conectado correctamente"
else
    echo "   ⚠️  Revisa los logs: docker logs n8n"
fi

echo ""
echo "✅ Proceso completado"
echo ""
echo "💡 Accede a n8n en: http://localhost:5678"


