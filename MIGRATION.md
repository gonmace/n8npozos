# Guía de Migración

Esta guía explica los cambios realizados en la estructura del proyecto.

## Cambios Principales

### Estructura de Directorios

**Antes:**
```
.
├── gradio/
│   └── app.py
├── docker-compose.yml
└── requirements.txt
```

**Después:**
```
.
├── src/
│   └── gradio/
│       ├── __init__.py
│       └── app.py
├── docker/
│   └── gradio/
│       ├── Dockerfile
│       └── Dockerfile.dev
├── deploy/
│   └── docker-compose.yml
├── config/
│   ├── development/
│   │   └── docker-compose.override.yml
│   └── production/
│       └── docker-compose.override.yml
├── scripts/
│   ├── dev.sh
│   ├── prod.sh
│   ├── stop.sh
│   ├── clean.sh
│   └── backup.sh
├── requirements.txt
├── requirements-dev.txt
└── Makefile
```

## Migración de Configuración

### 1. Variables de Entorno

El archivo `app.py` ahora usa variables de entorno. Asegúrate de tener un archivo `.env` con:

```bash
CHROMA_HOST=chroma
CHROMA_PORT=8000
CHROMA_COLLECTION=pozos
GRADIO_AUTH_USERNAME=admin
GRADIO_AUTH_PASSWORD=admin123
```

### 2. Comandos Docker Compose

**Antes:**
```bash
docker-compose up
```

**Después - Desarrollo:**
```bash
make dev
# O
docker-compose -f deploy/docker-compose.yml -f config/development/docker-compose.override.yml up
```

**Después - Producción:**
```bash
make prod
# O
docker-compose -f deploy/docker-compose.yml -f config/production/docker-compose.override.yml up -d
```

### 3. Rutas de Archivos

- `gradio/app.py` → `src/gradio/app.py`
- `docker-compose.yml` → `deploy/docker-compose.yml`
- Las referencias a `./gradio` ahora son `./src/gradio`

## Pasos para Migrar

1. **Backup de datos existentes**
   ```bash
   make backup
   ```

2. **Detener servicios antiguos**
   ```bash
   docker-compose -f deploy/docker-compose.yml down
   ```

3. **Copiar configuración de entorno**
   ```bash
   cp .env.example .env
   # Editar .env con tus valores
   ```

4. **Iniciar con nueva estructura**
   ```bash
   make dev  # Para desarrollo
   # O
   make prod # Para producción
   ```

## Verificación

Después de migrar, verifica que:

- ✅ Los servicios se inician correctamente
- ✅ Gradio está accesible en http://localhost:7860
- ✅ ChromaDB se conecta correctamente
- ✅ Los datos persisten en los volúmenes

## Rollback

Si necesitas volver a la estructura anterior:

1. Detener servicios nuevos: `docker-compose -f deploy/docker-compose.yml down`
2. Restaurar estructura de directorios anterior
3. Mover `deploy/docker-compose.yml` de vuelta a la raíz

