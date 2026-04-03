#!/bin/bash
# Genera el archivo de configuración de nginx desde el template y las variables del .env

set -e

ENV_FILE=".env"
TEMPLATE="deploy/nginx.conf.template"

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Error: Archivo .env no encontrado."
    exit 1
fi

if [ ! -f "$TEMPLATE" ]; then
    echo "❌ Error: Template de nginx no encontrado en $TEMPLATE"
    exit 1
fi

# Cargar variables del .env (ignorar comentarios y líneas vacías)
set -a
# shellcheck disable=SC1090
source <(grep -v '^\s*#' "$ENV_FILE" | grep -v '^\s*$' | sed 's/ *#.*//')
set +a

OUTPUT_FILE="${DOMAIN}.conf"

# Usar template sin SSL si los certificados aún no existen
if [ -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]; then
    TEMPLATE_USED="$TEMPLATE"
else
    TEMPLATE_USED="deploy/nginx.conf.nossl.template"
    echo "ℹ️  Certificados SSL no encontrados — usando configuración HTTP (solo puerto 80)"
fi

envsubst '${DOMAIN} ${N8N_PORT} ${GRADIO_PORT} ${API_PORT} ${DJANGO_PORT} ${MCP_PORT}' \
    < "$TEMPLATE_USED" > "$OUTPUT_FILE"

echo "✅ Configuración de nginx generada: $OUTPUT_FILE"
