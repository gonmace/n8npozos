#!/bin/bash
# Script para desarrollo local del API SIN Docker
# Ejecuta el API directamente en el sistema

set -e

echo "🚀 Iniciando API en desarrollo LOCAL (sin Docker)..."
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

# Instalar/actualizar dependencias del API
echo "📥 Instalando dependencias del API..."
pip install --upgrade pip -q
pip install -r src/api/requirements.txt -q

echo ""
echo "✅ Entorno configurado"
echo ""
echo "⚠️  IMPORTANTE: Para desarrollo local necesitas tener corriendo:"
echo "   - PostgreSQL (puerto 5432)"
echo "   - ChromaDB (puerto 8000)"
echo "   - n8n (puerto 5678) - opcional"
echo ""
echo "📋 Opciones:"
echo "   1. Usar Docker solo para servicios (PostgreSQL, ChromaDB, n8n):"
echo "      docker-compose --env-file .env -f deploy/docker-compose.yml up -d postgres chroma n8n"
echo ""
echo "   2. Ejecutar API localmente:"
echo "      python src/api/main.py"
echo ""
echo "   3. O ejecutar todo con este script:"
echo "      ./scripts/dev-api-local.sh"
echo ""

# Verificar si PostgreSQL y ChromaDB están corriendo
POSTGRES_RUNNING=false
CHROMA_RUNNING=false

if docker ps 2>/dev/null | grep -q postgres; then
    POSTGRES_RUNNING=true
    echo "✅ PostgreSQL está corriendo en Docker"
elif pg_isready -h localhost -p 5432 &>/dev/null 2>/dev/null; then
    POSTGRES_RUNNING=true
    echo "✅ PostgreSQL está corriendo localmente"
else
    echo "⚠️  PostgreSQL no está corriendo"
fi

if docker ps 2>/dev/null | grep -q chroma; then
    CHROMA_RUNNING=true
    echo "✅ ChromaDB está corriendo en Docker"
elif curl -s http://localhost:8000/api/v1/heartbeat &>/dev/null 2>/dev/null; then
    CHROMA_RUNNING=true
    echo "✅ ChromaDB está corriendo localmente"
else
    echo "⚠️  ChromaDB no está corriendo"
fi

echo ""
if [ "$POSTGRES_RUNNING" = false ] || [ "$CHROMA_RUNNING" = false ]; then
    echo "💡 Para iniciar solo los servicios necesarios:"
    echo "   make dev-services"
    echo ""
    read -p "¿Quieres iniciar los servicios ahora? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🚀 Iniciando servicios..."
        docker-compose --env-file .env -f deploy/docker-compose.yml up -d postgres chroma n8n
        echo "⏳ Esperando a que los servicios estén listos..."
        sleep 8
        
        # Verificar que ChromaDB esté listo
        echo "🔍 Verificando ChromaDB..."
        CHROMA_READY=false
        CHROMA_PORT_DETECTED=8008  # Por defecto (puerto mapeado de Docker)
        for i in {1..30}; do
            if curl -s http://localhost:8008/api/v2/heartbeat &>/dev/null || curl -s http://localhost:8008/api/v1/heartbeat &>/dev/null; then
                CHROMA_PORT_DETECTED=8008
                CHROMA_READY=true
                echo "✅ ChromaDB está listo en puerto 8008"
                break
            elif curl -s http://localhost:8000/api/v2/heartbeat &>/dev/null || curl -s http://localhost:8000/api/v1/heartbeat &>/dev/null; then
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
        echo "⚠️  Los servicios no están corriendo. El API puede fallar al iniciar."
        echo "   Ejecuta 'make dev-services' antes de continuar."
        exit 1
    fi
fi

# Configurar variables de entorno para desarrollo local
export API_HOST=${API_HOST:-0.0.0.0}
export API_PORT=${API_PORT:-8009}
export ENV=development
export DEBUG=true

# Configurar ChromaDB para desarrollo local
export CHROMA_HOST=localhost
export CHROMA_PORT=${CHROMA_PORT_DETECTED:-8008}  # Por defecto 8008 (puerto mapeado de Docker)

echo ""
echo "📋 Configuración:"
echo "   API_HOST=${API_HOST}"
echo "   API_PORT=${API_PORT}"
echo "   ENV=${ENV}"
echo "   DEBUG=${DEBUG}"
echo ""

echo "🎯 Iniciando API FastAPI localmente..."
echo "   Accede en: http://localhost:${API_PORT}"
echo "   Documentación: http://localhost:${API_PORT}/docs"
echo "   ReDoc: http://localhost:${API_PORT}/redoc"
echo "   Health: http://localhost:${API_PORT}/health"
echo ""
echo "   Presiona Ctrl+C para detener"
echo ""

# Ejecutar API desde el directorio raíz
cd "$(dirname "$0")/.."

# Asegurar que las variables estén exportadas para Python
export API_HOST
export API_PORT
export CHROMA_HOST
export CHROMA_PORT
export ENV
export DEBUG

# Cambiar al directorio del API para ejecutar
cd src/api
python main.py

