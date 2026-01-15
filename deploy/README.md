# Archivos Docker Compose

Este directorio contiene los archivos de configuración de Docker Compose para el proyecto.

## Archivos

- `docker-compose.yml` - Configuración principal del stack (n8n, PostgreSQL, ChromaDB, Gradio, API)

## Uso

Los archivos docker-compose se ejecutan desde la raíz del proyecto usando los scripts en `../scripts/` o el Makefile:

```bash
# Desarrollo
make dev
# O
./scripts/dev.sh

# Producción
make prod
# O
./scripts/prod.sh
```

## Notas

- Los archivos docker-compose usan rutas relativas desde la raíz del proyecto (`..`)
- Las variables de entorno se leen desde `.env` en la raíz del proyecto
- Los volúmenes y contextos de build están configurados para funcionar desde la raíz


