# N8N + ChromaDB + Gradio Stack

Stack completo para automatización con n8n, base de datos vectorial ChromaDB y panel de administración con Gradio.

## 📁 Estructura del Proyecto

```
.
├── src/                    # Código fuente
│   ├── gradio/            # Aplicación Gradio
│   │   └── app.py         # Panel de administración ChromaDB
│   └── api/               # Microservicio API
│       ├── main.py        # API REST con FastAPI
│       └── requirements.txt
├── docker/                # Dockerfiles
│   ├── gradio/
│   │   ├── Dockerfile     # Imagen de producción
│   │   └── Dockerfile.dev # Imagen de desarrollo
│   └── api/
│       ├── Dockerfile     # Imagen de producción
│       └── Dockerfile.dev # Imagen de desarrollo
├── config/                # Configuraciones por entorno
│   ├── development/       # Configuración de desarrollo
│   └── production/        # Configuración de producción
├── scripts/               # Scripts de utilidad
│   ├── dev.sh            # Iniciar desarrollo
│   ├── prod.sh           # Iniciar producción
│   ├── stop.sh           # Detener servicios
│   ├── clean.sh          # Limpiar recursos
│   └── backup.sh         # Backup de volúmenes
├── deploy/                # Archivos Docker Compose
│   ├── docker-compose.yml        # Configuración principal
│   └── docker-compose-pliego.yml # Configuración alternativa
├── requirements.txt       # Dependencias Python (producción)
├── requirements-dev.txt   # Dependencias Python (desarrollo)
└── .env.example          # Plantilla de variables de entorno
```

## 🚀 Inicio Rápido

### Prerrequisitos

- Docker y Docker Compose instalados
- Git

### Desarrollo

#### Opción 1: Desarrollo Local (Recomendado - Sin Docker para la app)

1. **Clonar el repositorio** (si aplica)
   ```bash
   git clone <repo-url>
   cd n8n
   ```

2. **Configurar variables de entorno**
   ```bash
   cp .env.example .env
   # Editar .env con tus valores
   ```

3. **Iniciar desarrollo local**
   ```bash
   make dev
   # O directamente:
   ./scripts/dev-local.sh
   ```
   
   Esto:
   - Crea un entorno virtual Python
   - Instala dependencias
   - Inicia solo PostgreSQL y ChromaDB en Docker (si no están corriendo)
   - Ejecuta la aplicación Gradio localmente (sin Docker)
   
   **Ventajas:**
   - ✅ Hot-reload automático (cambios se reflejan inmediatamente)
   - ✅ Debugging más fácil
   - ✅ Sin necesidad de reconstruir imágenes Docker
   - ✅ Más rápido para desarrollo

#### Opción 2: Desarrollo con Docker (Todo containerizado)

Si prefieres desarrollo completamente containerizado:

```bash
make dev-docker
# O directamente:
./scripts/dev-docker.sh
```

#### Desarrollo del API (Microservicio)

Para ejecutar el API localmente en desarrollo:

```bash
make dev-api
# O directamente:
./scripts/dev-api-local.sh
```

Esto ejecuta el API FastAPI localmente con hot-reload.

#### Solo Servicios (PostgreSQL, ChromaDB, n8n)

Si solo necesitas los servicios de base de datos:

```bash
make dev-services
# O directamente:
./scripts/dev-services.sh
```

**Servicios disponibles:**
   - **n8n**: http://localhost:5678
   - **Gradio**: http://localhost:7860
   - **API**: http://localhost:8009 (docs en /docs)
   - **ChromaDB**: http://localhost:8000 (local) o 8008 (Docker)
   - **PostgreSQL**: localhost:5432

### Producción

1. **Configurar variables de entorno**
   ```bash
   cp .env.example .env
   # Editar .env con valores de producción seguros
   ```

2. **Iniciar entorno de producción**
   ```bash
   make prod
   # O directamente:
   ./scripts/prod.sh
   ```

## 📋 Comandos Disponibles

Usa `make help` para ver todos los comandos disponibles, o:

- `make dev` - Iniciar desarrollo (Gradio local)
- `make dev-api` - Iniciar API en desarrollo local
- `make dev-services` - Iniciar solo servicios (PostgreSQL, ChromaDB, n8n)
- `make prod` - Iniciar producción
- `make stop` - Detener servicios (desarrollo por defecto)
- `make stop ENV=production` - Detener producción
- `make logs` - Ver logs de todos los servicios
- `make logs-gradio` - Ver logs de Gradio
- `make logs-api` - Ver logs del API
- `make backup` - Crear backup de volúmenes
- `make clean` - Limpiar contenedores, imágenes y volúmenes
- `make shell-gradio` - Abrir shell en contenedor Gradio
- `make shell-api` - Abrir shell en contenedor API
- `make shell-postgres` - Abrir psql en PostgreSQL
- `make shell-n8n` - Abrir shell en contenedor n8n

## 🔧 Configuración

### Variables de Entorno

Copia `.env.example` a `.env` y configura:

```bash
# PostgreSQL
POSTGRES_USER=magoreal
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=pozos

# N8N
N8N_ENCRYPTION_KEY=your_encryption_key
N8N_USER_MANAGEMENT_JWT_SECRET=your_jwt_secret
N8N_HOST=your-domain.com

# Gradio
GRADIO_AUTH_USERNAME=admin
GRADIO_AUTH_PASSWORD=admin123
CHROMA_HOST=chroma
CHROMA_PORT=8000
CHROMA_COLLECTION=pozos

# Configuración de Embeddings (OpenAI)
OPENAI_API_KEY=your_openai_api_key_here
EMBEDDING_MODEL=text-embedding-3-large
```

### Desarrollo vs Producción

- **Desarrollo Local** (`make dev`): App ejecutada directamente, sin Docker. Hot-reload automático. Solo servicios (PostgreSQL, ChromaDB) en Docker.
- **Desarrollo Docker** (`make dev-docker`): Todo containerizado con volúmenes montados para hot-reload
- **Producción** (`make prod`): Todo en Docker, imágenes optimizadas, sin volúmenes de desarrollo

## 🐳 Servicios Docker

### n8n
- **Puerto**: 5678
- **Imagen**: n8nio/n8n:2.0.2
- **Base de datos**: PostgreSQL

### PostgreSQL
- **Puerto**: 5432
- **Imagen**: postgres:16-alpine
- **Volumen**: postgres_storage

### ChromaDB
- **Puerto**: 8008
- **Imagen**: chromadb/chroma:1.3.8.dev16
- **Volumen**: chroma_storage

### Gradio
- **Puerto**: 7860
- **Imagen**: Construida desde `docker/gradio/Dockerfile`
- **Código**: `src/gradio/app.py`

## 🔒 Seguridad

- ⚠️ **Nunca** commitees archivos `.env` al repositorio
- ⚠️ Cambia las credenciales por defecto en producción
- ⚠️ Usa contraseñas seguras y únicas para cada entorno
- ⚠️ Configura firewall adecuadamente en producción

## 📦 Backup y Restauración

### Crear Backup
```bash
make backup
```

Los backups se guardan en `./backups/` con timestamp.

### Restaurar (ejemplo PostgreSQL)
```bash
docker run --rm \
  -v postgres_storage:/data \
  -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/postgres_YYYYMMDD_HHMMSS.tar.gz -C /data
```

## 🛠️ Desarrollo

### Estructura de Código

- `src/gradio/app.py`: Aplicación principal de Gradio
- Las dependencias se gestionan en `requirements.txt` (producción) y `requirements-dev.txt` (desarrollo)

### Agregar Nuevas Dependencias

1. **Producción**: Agregar a `requirements.txt`
2. **Desarrollo**: Agregar a `requirements-dev.txt`
3. **Reinstalar**: En desarrollo local, ejecuta `pip install -r requirements-dev.txt` en el entorno virtual

### Hot Reload en Desarrollo

- **Desarrollo Local** (`make dev`): Los cambios se reflejan automáticamente al guardar (sin necesidad de reiniciar)
- **Desarrollo Docker** (`make dev-docker`): Los cambios se reflejan gracias al volumen montado

### Configuración para Desarrollo Local

En desarrollo local, la aplicación se conecta a:
- **ChromaDB**: `localhost:8000` (si ChromaDB está en Docker con mapeo de puerto) o `localhost:8008`
- **PostgreSQL**: `localhost:5432`

Asegúrate de que tu `.env` tenga:
```bash
CHROMA_HOST=localhost
CHROMA_PORT=8000  # o 8008 si usas el puerto mapeado de Docker
```

### Flujo de Trabajo Recomendado

1. **Primera vez**: `make dev` (crea venv e instala dependencias)
2. **Desarrollo diario**: 
   - `make dev-services` (inicia solo PostgreSQL y ChromaDB en Docker)
   - `python src/gradio/app.py` (ejecuta la app directamente desde `src/gradio/`)
3. **Testing**: `make dev-docker` (prueba en entorno similar a producción)
4. **Despliegue**: `make prod` (producción con Docker)

## 📝 Notas

- Los volúmenes de Docker persisten los datos entre reinicios
- Usa `make clean` con precaución, elimina todos los datos
- En producción, considera usar un reverse proxy (nginx, traefik) para HTTPS

## 🤝 Contribuir

1. Crear rama para nueva funcionalidad
2. Hacer cambios en desarrollo
3. Probar con `make dev`
4. Crear pull request

## 📄 Licencia

[Tu licencia aquí]

