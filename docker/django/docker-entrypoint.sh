#!/bin/sh
set -e
echo "Running Django migrations..."
python manage.py migrate --noinput
echo "Starting gunicorn..."
exec "$@"
