#!/bin/bash
# Script para desarrollo local SIN Docker
# Ejecuta servicios directamente en el sistema

set -e

echo "🚀 Iniciando entorno de desarrollo LOCAL (sin Docker)..."
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

# Cargar variables de entorno desde .env
if [ -f .env ]; then
    set -a  # Exportar todas las variables automáticamente
    source .env
    set +a  # Desactivar exportación automática
    echo "✅ Variables de entorno cargadas desde .env"
else
    echo "⚠️  Archivo .env no encontrado"
fi

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python3 no está instalado"
    exit 1
fi

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv
fi

# Activar entorno virtual
echo "🔌 Activando entorno virtual..."
source venv/bin/activate

# Instalar/actualizar dependencias
echo "📥 Instalando dependencias..."
pip install --upgrade pip -q
pip install -r requirements-dev.txt -q

echo ""
echo "✅ Entorno configurado"
echo ""
echo "⚠️  IMPORTANTE: Para desarrollo local necesitas tener corriendo:"
echo "   - PostgreSQL (puerto 5432)"
echo "   - ChromaDB (puerto 8000)"
echo "   - n8n (puerto 5678)"
echo ""
echo "📋 Opciones:"
echo "   1. Usar Docker solo para servicios (PostgreSQL, ChromaDB, n8n):"
echo "      docker compose --env-file .env -f deploy/docker-compose.yml up -d postgres chroma n8n"
echo ""
echo "   2. Ejecutar Gradio localmente:"
echo "      python src/gradio/app.py"
echo ""
echo "   3. O ejecutar todo con este script (solo Gradio local):"
echo "      ./scripts/dev-local.sh"
echo ""

# Verificar si PostgreSQL, ChromaDB y n8n están corriendo
POSTGRES_RUNNING=false
CHROMA_RUNNING=false
N8N_RUNNING=false

if docker ps 2>/dev/null | grep -qE "(n8npozos-postgres|postgres)"; then
    POSTGRES_RUNNING=true
    echo "✅ PostgreSQL está corriendo en Docker"
elif pg_isready -h localhost -p 5432 &>/dev/null; then
    POSTGRES_RUNNING=true
    echo "✅ PostgreSQL está corriendo localmente"
else
    echo "⚠️  PostgreSQL no está corriendo"
fi

if docker ps 2>/dev/null | grep -qE "(n8npozos-chroma|chroma)"; then
    CHROMA_RUNNING=true
    echo "✅ ChromaDB está corriendo en Docker"
elif curl -s http://localhost:8000/api/v1/heartbeat &>/dev/null; then
    CHROMA_RUNNING=true
    echo "✅ ChromaDB está corriendo localmente"
else
    echo "⚠️  ChromaDB no está corriendo"
fi

if docker ps 2>/dev/null | grep -qE "(n8npozos-n8n|n8n)"; then
    N8N_RUNNING=true
    echo "✅ n8n está corriendo en Docker"
elif curl -s http://localhost:5678 &>/dev/null; then
    N8N_RUNNING=true
    echo "✅ n8n está corriendo localmente"
else
    echo "⚠️  n8n no está corriendo"
fi

echo ""
if [ "$POSTGRES_RUNNING" = false ] || [ "$CHROMA_RUNNING" = false ] || [ "$N8N_RUNNING" = false ]; then
    echo "💡 Para iniciar solo los servicios necesarios:"
    echo "   make dev-services"
    echo ""
    read -p "¿Quieres iniciar los servicios ahora? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🚀 Iniciando servicios..."
        docker compose --env-file .env -f deploy/docker-compose.yml up -d postgres chroma n8n
        echo "⏳ Esperando a que los servicios estén listos..."
        sleep 8
        
        # Verificar que ChromaDB esté listo
        echo "🔍 Verificando ChromaDB..."
        CHROMA_READY=false
        for i in {1..30}; do
            if curl -s http://localhost:8008/api/v1/heartbeat &>/dev/null; then
                CHROMA_PORT_DETECTED=8008
                CHROMA_READY=true
                echo "✅ ChromaDB está listo en puerto 8008"
                break
            elif curl -s http://localhost:8000/api/v1/heartbeat &>/dev/null; then
                CHROMA_PORT_DETECTED=8000
                CHROMA_READY=true
                echo "✅ ChromaDB está listo en puerto 8000"
                break
            fi
            if [ $i -eq 30 ]; then
                echo "⚠️  ChromaDB no responde después de 30 intentos"
                CHROMA_PORT_DETECTED=8008  # Por defecto
            else
                sleep 1
            fi
        done
    else
        echo ""
        echo "⚠️  Los servicios no están corriendo. La aplicación fallará al iniciar."
        echo "   Ejecuta 'make dev-services' antes de continuar."
        exit 1
    fi
fi

# Configurar variables de entorno para desarrollo local
export CHROMA_HOST=localhost
export CHROMA_PORT=${CHROMA_PORT_DETECTED:-8008}  # Por defecto 8008 (puerto mapeado de Docker)
export ENV=development

# Configurar puerto de Gradio (verificar si está disponible)
GRADIO_SERVER_PORT=${GRADIO_SERVER_PORT:-7860}
if lsof -Pi :${GRADIO_SERVER_PORT} -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Puerto ${GRADIO_SERVER_PORT} está en uso"
    PID=$(lsof -ti :${GRADIO_SERVER_PORT} 2>/dev/null | head -1)
    if [ ! -z "$PID" ]; then
        echo "   Proceso usando el puerto: PID $PID"
        echo "   Comando: $(ps -p $PID -o cmd= 2>/dev/null | head -1)"
    fi
    echo ""
    echo "💡 Opciones:"
    echo "   1. Detener el proceso: kill $PID"
    echo "   2. Usar otro puerto: GRADIO_SERVER_PORT=7861 make dev"
    echo ""
    read -p "¿Quieres detener el proceso y usar el puerto ${GRADIO_SERVER_PORT}? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kill $PID 2>/dev/null && sleep 2 && echo "✅ Proceso detenido" || echo "⚠️  No se pudo detener el proceso"
    else
        echo "❌ No se puede iniciar Gradio. El puerto ${GRADIO_SERVER_PORT} está ocupado."
        echo "   Usa otro puerto: GRADIO_SERVER_PORT=7861 make dev"
        exit 1
    fi
fi

echo ""
echo "📋 Configuración:"
echo "   CHROMA_HOST=${CHROMA_HOST}"
echo "   CHROMA_PORT=${CHROMA_PORT}"
echo "   GRADIO_SERVER_PORT=${GRADIO_SERVER_PORT}"
echo ""

echo "🎯 Iniciando aplicación Gradio localmente..."
echo "   Accede en: http://localhost:${GRADIO_SERVER_PORT}"
echo "   Usuario: ${GRADIO_AUTH_USERNAME:-admin}"
echo "   ChromaDB: ${CHROMA_HOST}:${CHROMA_PORT}"
echo "   n8n: http://localhost:5678"
echo ""

# Verificar configuración de OpenAI
if [ -z "$OPENAI_API_KEY" ]; then
    echo "   ⚠️  OPENAI_API_KEY no está configurada en .env"
    echo "   Los embeddings usarán el modelo por defecto de ChromaDB"
else
    echo "   ✅ OPENAI_API_KEY configurada"
    echo "   ✅ Modelo: ${EMBEDDING_MODEL:-text-embedding-3-large}"
fi

echo ""
echo "   Presiona Ctrl+C para detener"
echo ""

# Ejecutar aplicación Gradio desde el directorio raíz
# Las variables de entorno ya están cargadas desde .env
cd "$(dirname "$0")/.."

# Asegurar que las variables estén exportadas para Python
export OPENAI_API_KEY
export EMBEDDING_MODEL=${EMBEDDING_MODEL:-text-embedding-3-large}
export CHROMA_HOST
export CHROMA_PORT
export GRADIO_SERVER_PORT
export ENV=development

python src/gradio/app.py

