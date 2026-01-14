# 🚀 Guía Rápida de Comandos

## ⚠️ IMPORTANTE: Siempre usar `--env-file .env`

Cuando ejecutes comandos `docker compose` directamente (sin usar `make`), **SIEMPRE** incluye `--env-file .env`:

```bash
# ✅ CORRECTO
docker compose --env-file .env -f deploy/docker-compose.yml logs -f

# ❌ INCORRECTO (no lee las variables de entorno)
docker compose -f deploy/docker-compose.yml logs -f
```

## 📋 Comandos Recomendados (usando Make)

Usa estos comandos que ya incluyen `--env-file .env`:

```bash
# Ver logs
make logs              # Todos los servicios
make logs-n8n         # Solo n8n
make logs-gradio       # Solo Gradio
make logs-api          # Solo API

# Gestión de servicios
make prod              # Iniciar producción
make stop              # Detener servicios
make rebuild           # Reconstruir imágenes

# Shells
make shell-postgres    # Acceder a PostgreSQL
make shell-n8n         # Acceder a n8n
make shell-api         # Acceder a API
```

## 🔧 Comandos Docker Compose Directos

Si necesitas ejecutar comandos directamente, **siempre** incluye `--env-file .env`:

```bash
# Ver logs
docker compose --env-file .env -f deploy/docker-compose.yml logs -f

# Ver estado
docker compose --env-file .env -f deploy/docker-compose.yml ps

# Reiniciar un servicio
docker compose --env-file .env -f deploy/docker-compose.yml restart n8n

# Detener servicios
docker compose --env-file .env -f deploy/docker-compose.yml down

# Iniciar servicios
docker compose --env-file .env -f deploy/docker-compose.yml up -d
```

## 🐛 Solución de Problemas

### Variables de entorno no se leen

Si ves advertencias como:
```
WARN[0000] The "POSTGRES_USER" variable is not set. Defaulting to a blank string.
```

**Solución:** Asegúrate de usar `--env-file .env` en todos los comandos `docker compose`.

### Verificar que .env existe y tiene valores

```bash
# Verificar que el archivo existe
ls -la .env

# Ver las variables (sin mostrar valores sensibles)
grep -E "^[A-Z_]+=" .env | cut -d'=' -f1
```

### Crear .env si no existe

```bash
./scripts/create-env.sh
nano .env  # Editar con tus valores
```
