# 🔧 Flujo de Desarrollo - Cómo Funciona `make dev`

## Resumen

`make dev` ejecuta **Gradio localmente** (sin Docker) pero necesita que los **servicios** (PostgreSQL, ChromaDB, n8n) estén corriendo en Docker.

## Comandos Disponibles

### 1. `make dev` - Desarrollo Local (Gradio sin Docker)

**Qué hace:**
- ✅ Ejecuta `scripts/dev-local.sh`
- ✅ **NO ejecuta docker-compose directamente**
- ✅ Verifica si PostgreSQL, ChromaDB y n8n están corriendo
- ✅ Si no están corriendo, pregunta si quieres iniciarlos
- ✅ Si aceptas, ejecuta: `docker compose --env-file .env -f deploy/docker-compose.yml up -d postgres chroma n8n`
- ✅ Luego ejecuta **Gradio localmente** (sin Docker) en el puerto 7860

**Archivos docker-compose usados:**
- Solo `deploy/docker-compose.yml` (sin override)
- Solo para los servicios: `postgres`, `chroma`, `n8n`

**Ventajas:**
- Hot-reload rápido (cambios en código se reflejan inmediatamente)
- Debugging más fácil
- Desarrollo más rápido

---

### 2. `make dev-services` - Solo Servicios en Docker

**Qué hace:**
- ✅ Ejecuta `scripts/dev-services.sh`
- ✅ Ejecuta: `docker compose --env-file .env -f deploy/docker-compose.yml up -d postgres chroma n8n`
- ✅ Solo inicia los servicios base, NO Gradio ni API

**Archivos docker-compose usados:**
- Solo `deploy/docker-compose.yml`

**Cuándo usarlo:**
- Cuando quieres iniciar solo los servicios y ejecutar Gradio/API manualmente
- Antes de ejecutar `make dev` si los servicios no están corriendo

---

### 3. `make dev-docker` - Todo en Docker

**Qué hace:**
- ✅ Ejecuta `scripts/dev-docker.sh`
- ✅ Ejecuta: `docker compose --env-file .env -f deploy/docker-compose.yml -f config/development/docker-compose.override.yml up`
- ✅ Inicia **TODO** en Docker: PostgreSQL, ChromaDB, n8n, Gradio, API

**Archivos docker-compose usados:**
- `deploy/docker-compose.yml` (base)
- `config/development/docker-compose.override.yml` (override para desarrollo)

**Ventajas:**
- Entorno completamente aislado
- Mismo comportamiento que producción
- Hot-reload con volúmenes montados

---

## Flujo Típico de Desarrollo

### Opción A: Desarrollo Local (Recomendado)

```bash
# 1. Iniciar solo los servicios
make dev-services

# 2. En otra terminal, iniciar Gradio localmente
make dev
```

**Archivos docker-compose:**
- Solo `deploy/docker-compose.yml` para servicios

---

### Opción B: Todo en Docker

```bash
# Iniciar todo en Docker (incluye Gradio y API)
make dev-docker
```

**Archivos docker-compose:**
- `deploy/docker-compose.yml` (base)
- `config/development/docker-compose.override.yml` (override)

---

## Archivos Docker Compose

### `deploy/docker-compose.yml`
- **Archivo principal** con todos los servicios
- Usado por todos los comandos
- Define: PostgreSQL, ChromaDB, n8n, Gradio, API

### `config/development/docker-compose.override.yml`
- **Solo usado por `make dev-docker`**
- Override para desarrollo:
  - Monta código fuente como volúmenes (hot-reload)
  - Usa Dockerfiles de desarrollo
  - Configuración de debug

### `config/production/docker-compose.override.yml`
- **Solo usado por `make prod`**
- Override para producción:
  - Sin volúmenes de código fuente
  - Usa imágenes construidas
  - Configuración optimizada

---

## Resumen de Archivos Usados

| Comando | docker-compose.yml | development override | production override |
|---------|-------------------|---------------------|-------------------|
| `make dev` | ✅ (solo servicios) | ❌ | ❌ |
| `make dev-services` | ✅ (solo servicios) | ❌ | ❌ |
| `make dev-docker` | ✅ | ✅ | ❌ |
| `make prod` | ✅ | ❌ | ✅ |

---

## Ejemplo Práctico

```bash
# Desarrollo local típico:
make dev-services    # Inicia servicios en Docker
make dev            # Ejecuta Gradio localmente (hot-reload)

# O todo en Docker:
make dev-docker     # Todo containerizado con hot-reload
```
