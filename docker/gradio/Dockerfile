FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema si es necesario
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Actualizar pip primero
RUN pip install --upgrade pip

# Copiar requirements primero para aprovechar cache de Docker
COPY requirements.txt /app/
# Usar timeout más largo y retries para evitar problemas de red
RUN pip install --no-cache-dir --progress-bar on \
    --default-timeout=100 \
    --retries 5 \
    -r requirements.txt

# Copiar código de la aplicación
COPY src/gradio /app

# Exponer puerto
EXPOSE 7860

# Comando por defecto
CMD ["python", "app.py"]

