# Microservicio API

Microservicio de ejemplo implementado con FastAPI.

## Características

- API REST con FastAPI
- Documentación automática en `/docs` (Swagger UI)
- Health check en `/health`
- Endpoints CRUD de ejemplo para items
- CORS configurado
- Variables de entorno para configuración

## Endpoints

### Información y Health
- `GET /` - Información del servicio
- `GET /health` - Health check

### ChromaDB Collections
- `GET /chroma/collections` - Listar todas las colecciones
- `GET /chroma/collections/{collection_name}` - Obtener vectores de una colección
- `GET /chroma/collections/{collection_name}/info` - Información de una colección

### Retrievers
- `POST /retrievers/collections/{collection_name}/mmr` - Búsqueda MMR (Maximum Marginal Relevance)

### Items (Ejemplo)
- `GET /items` - Listar todos los items
- `GET /items/{item_id}` - Obtener un item por ID
- `POST /items` - Crear un nuevo item
- `PUT /items/{item_id}` - Actualizar un item
- `DELETE /items/{item_id}` - Eliminar un item

## Variables de Entorno

- `API_HOST` - Host del servidor (default: 0.0.0.0)
- `API_PORT` - Puerto del servidor (default: 8009)
- `ENV` - Entorno (development/production)
- `DEBUG` - Modo debug (true/false)

## Uso

### Desarrollo Local (Recomendado)

Ejecuta el API localmente sin Docker para desarrollo rápido con hot-reload:

```bash
# Opción 1: Usar el script (recomendado)
make dev-api

# Opción 2: Ejecutar directamente
./scripts/dev-api-local.sh
```

El script:
- ✅ Verifica que los servicios (PostgreSQL, ChromaDB, n8n) estén corriendo
- ✅ Crea/activa el entorno virtual automáticamente
- ✅ Instala las dependencias necesarias
- ✅ Configura las variables de entorno
- ✅ Inicia el API con hot-reload (los cambios se reflejan automáticamente)

**Nota**: Asegúrate de tener los servicios corriendo primero:
```bash
make dev-services
```

### Con Docker Compose

```bash
# Iniciar el servicio
docker-compose --env-file .env -f deploy/docker-compose.yml up -d api

# Ver logs
docker-compose --env-file .env -f deploy/docker-compose.yml logs -f api

# Detener
docker-compose --env-file .env -f deploy/docker-compose.yml stop api
```

### Desarrollo con Docker (hot-reload)

```bash
docker-compose --env-file .env \
  -f deploy/docker-compose.yml \
  -f config/development/docker-compose.override.yml \
  up api
```

### Manualmente (sin scripts)

```bash
cd src/api
pip install -r requirements.txt
python main.py
```

## Documentación

Una vez iniciado, accede a:
- Swagger UI: http://localhost:8009/docs
- ReDoc: http://localhost:8009/redoc

## Ejemplos de uso

### Búsqueda MMR

```bash
# Búsqueda MMR en una colección
curl -X POST "http://localhost:8009/retrievers/collections/pozos/mmr" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Warnes",
    "k": 4,
    "fetch_k": 20,
    "lambda_mult": 0.5,
    "filters": null
  }'
```

### ChromaDB Collections

```bash
# Listar colecciones
curl "http://localhost:8009/chroma/collections"

# Obtener vectores de una colección
curl "http://localhost:8009/chroma/collections/pozos"

# Información de una colección
curl "http://localhost:8009/chroma/collections/pozos/info"
```

### Items (Ejemplo)

```bash
# Crear un item
curl -X POST "http://localhost:8009/items" \
  -H "Content-Type: application/json" \
  -d '{"name": "Item 1", "description": "Descripción", "price": 10.99}'

# Listar items
curl "http://localhost:8009/items"

# Obtener un item
curl "http://localhost:8009/items/1"
```

