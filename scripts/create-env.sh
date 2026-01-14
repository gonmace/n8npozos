#!/bin/bash
# Script para crear archivo .env desde plantilla

set -e

ENV_FILE=".env"
ENV_EXAMPLE=".env.example"

if [ -f "$ENV_FILE" ]; then
    echo "⚠️  El archivo .env ya existe."
    read -p "   ¿Deseas sobrescribirlo? (s/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        echo "❌ Operación cancelada"
        exit 1
    fi
fi

echo "📝 Creando archivo .env..."

cat > "$ENV_FILE" << 'EOF'
# =====================================================
# Variables de Entorno - Producción
# =====================================================
# IMPORTANTE: Configura todos los valores antes de usar make prod

# =====================================================
# PostgreSQL
# =====================================================
POSTGRES_USER=magoreal
POSTGRES_PASSWORD=changeme_secure_password_here
POSTGRES_DB=pozos

# =====================================================
# N8N
# =====================================================
# Clave de encriptación (genera una nueva con: openssl rand -base64 32)
N8N_ENCRYPTION_KEY=your_encryption_key_here_generate_new_one

# JWT Secret para autenticación (genera una nueva con: openssl rand -base64 32)
N8N_USER_MANAGEMENT_JWT_SECRET=your_jwt_secret_here_generate_new_one

# Host de n8n (tu dominio)
N8N_HOST=n8npozos.magoreal.com

# =====================================================
# ChromaDB
# =====================================================
# En Docker, usar el nombre del servicio (chroma) y puerto interno (8000)
CHROMA_HOST=chroma
CHROMA_PORT=8000
CHROMA_COLLECTION=pozos

# =====================================================
# Gradio
# =====================================================
GRADIO_AUTH_USERNAME=admin
GRADIO_AUTH_PASSWORD=admin123_change_this
ENV=production
DEBUG=false

# =====================================================
# OpenAI (para embeddings)
# =====================================================
OPENAI_API_KEY=your_openai_api_key_here
EMBEDDING_MODEL=text-embedding-3-large

# =====================================================
# API Microservicio
# =====================================================
API_HOST=0.0.0.0
API_PORT=8009
EOF

echo "✅ Archivo .env creado"
echo ""
echo "⚠️  IMPORTANTE: Debes editar .env y configurar:"
echo "   1. POSTGRES_PASSWORD - Cambia por una contraseña segura"
echo "   2. N8N_ENCRYPTION_KEY - Genera una nueva clave"
echo "   3. N8N_USER_MANAGEMENT_JWT_SECRET - Genera una nueva clave"
echo "   4. N8N_HOST - Tu dominio real"
echo "   5. OPENAI_API_KEY - Tu clave de API de OpenAI"
echo "   6. GRADIO_AUTH_PASSWORD - Cambia por una contraseña segura"
echo ""
echo "💡 Para generar claves seguras:"
echo "   openssl rand -base64 32"
echo ""
echo "📝 Edita el archivo con:"
echo "   nano .env"
