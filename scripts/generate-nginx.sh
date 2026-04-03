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

envsubst '${DOMAIN} ${N8N_PORT} ${GRADIO_PORT} ${API_PORT} ${DJANGO_PORT} ${MCP_PORT}' \
    < "$TEMPLATE" > "$OUTPUT_FILE"

echo "✅ Configuración de nginx generada: $OUTPUT_FILE"
echo ""
echo "Para instalarla en el servidor:"
echo "  sudo cp $OUTPUT_FILE /etc/nginx/sites-available/$OUTPUT_FILE"
echo "  sudo ln -sf /etc/nginx/sites-available/$OUTPUT_FILE /etc/nginx/sites-enabled/$OUTPUT_FILE"
echo "  sudo nginx -t && sudo systemctl reload nginx"
echo ""
echo "Para HTTPS con certbot (después de instalar nginx):"
echo "  sudo certbot --nginx -d ${DOMAIN}"
