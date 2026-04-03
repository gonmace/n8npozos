FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs npm \
    && rm -rf /var/lib/apt/lists/*

COPY dj/requirements.txt /app/
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY dj/core /app/core
COPY dj/dashboard /app/dashboard
COPY dj/audit /app/audit
COPY dj/theme /app/theme
COPY dj/manage.py /app/
# Scripts Python que usa el módulo audit para procesar chats
COPY scripts/parse_whatsapp_chats.py /app/scripts/
COPY scripts/enviar_mensajes_chatbot.py /app/scripts/

# Build Tailwind al construir la imagen
WORKDIR /app/theme/static_src
RUN npm install
RUN npm run build

WORKDIR /app

# collectstatic con dummy key (se sobreescribe en runtime)
ARG DJANGO_SECRET_KEY=build-dummy-key
ENV DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
ENV DJANGO_DB=
RUN python manage.py collectstatic --noinput

EXPOSE 8000

COPY docker/django/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120", "core.wsgi:application"]
