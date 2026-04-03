#!/bin/bash
# Se ejecuta automáticamente en el primer arranque de PostgreSQL
# (directorio /docker-entrypoint-initdb.d/)
set -e

echo "Creando bases de datos: n8n, n8n_django..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE n8n;
    CREATE DATABASE n8n_django;
EOSQL

echo "Bases de datos creadas."
