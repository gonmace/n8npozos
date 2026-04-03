# N8N + ChromaDB + Gradio + Django Stack

Stack completo para automatización con n8n, base de datos vectorial ChromaDB, panel de administración Gradio, microservicio API de búsqueda semántica y dashboard Django para monitoreo y auditoría de conversaciones WhatsApp.

## Servicios

| Servicio | Descripción | Producción | Desarrollo local |
|---|---|---|---|
| **n8n** | Motor de automatización de workflows | `https://dominio.com/` | http://localhost:5679 |
| **Django Dashboard** | Monitoreo y auditoría de conversaciones | `https://dominio.com/dashboard/` | http://localhost:8010 |
| **Gradio** | Panel admin de ChromaDB (embeddings) | `https://dominio.com/gradio/` | http://localhost:7860 |
| **API** | Búsqueda MMR sobre ChromaDB (FastAPI) | `https://dominio.com/api/` | http://localhost:8009 |
| **n8n-MCP** | Servidor MCP para AI IDEs | `https://dominio.com/mcp` | http://localhost:3001/mcp |
| **PostgreSQL** | Base de datos de n8n y Django | interno | localhost:5433 |
| **ChromaDB** | Base de datos vectorial | interno | localhost:8008 |

Nginx corre en el host y enruta el tráfico a los contenedores Docker.

---

## Estructura del Proyecto

```
.
├── dj/                        # Dashboard Django (monitoreo/auditoría)
│   ├── core/                  # Configuración del proyecto Django
│   ├── dashboard/             # App: workflows, ejecuciones, historial de chats
│   ├── audit/                 # App: auditoría de prompts y conversaciones
│   └── theme/                 # Tailwind CSS + daisyUI (fuente en static_src/)
├── src/
│   ├── gradio/app.py          # Panel admin ChromaDB
│   └── api/main.py            # API REST — endpoint MMR
├── docker/
│   ├── django/Dockerfile      # Imagen Django (incluye build de Tailwind + collectstatic)
│   ├── gradio/Dockerfile
│   └── api/Dockerfile
├── deploy/
│   ├── docker-compose.yml     # Stack completo (7 servicios)
│   └── nginx.conf.template    # Template de nginx (usa envsubst)
├── config/
│   ├── production/            # Override docker-compose para producción
│   └── development/           # Override docker-compose para desarrollo local
├── scripts/
│   ├── prod.sh                # Levantar producción
│   ├── backup.sh              # Backup de datos → backups/
│   ├── restore.sh             # Restaurar desde backups/
│   ├── generate-nginx.sh      # Generar config de nginx desde .env
│   ├── init-database.sh       # Crear bases de datos (pozos + n8n_django)
│   ├── parse_whatsapp_chats.py   # Parsear exports .txt de WhatsApp
│   └── enviar_mensajes_chatbot.py # Simular conversaciones para testing
├── n8n_storage/               # Datos de n8n — workflows, credenciales, config (no en git)
├── postgres_storage/          # Datos de PostgreSQL (no en git)
├── chroma_storage/            # Datos de ChromaDB (no en git)
├── shared/                    # Archivos compartidos con n8n (File nodes, no en git)
├── chats/                     # Exports WhatsApp para auditoría (no en git)
├── workflows/                 # Backups de workflows n8n en JSON (no en git)
├── backups/                   # Backups comprimidos .tar.gz (no en git)
├── .env                       # Variables de entorno (no en git)
└── .env.example               # Template de variables con descripción
```

> Los directorios `n8n_storage/`, `postgres_storage/` y `chroma_storage/` son bind mounts directos — los datos viven en el proyecto, no en volúmenes Docker nombrados. Esto facilita backups, migraciones y hace el proyecto completamente autocontenido.

---

## Deployment en nuevo servidor

### Prerrequisitos

```bash
# Docker y Docker Compose
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Nginx
sudo apt install nginx -y
```

### 1. Clonar y configurar

```bash
git clone https://github.com/gonmace/n8npozos.git
cd n8npozos
cp .env.example .env
nano .env
```

Variables mínimas a cambiar en `.env`:

| Variable | Cómo generarla |
|---|---|
| `DOMAIN` | tu dominio real (sin https://) |
| `POSTGRES_PASSWORD` | password seguro |
| `N8N_ENCRYPTION_KEY` | `openssl rand -base64 32` |
| `N8N_USER_MANAGEMENT_JWT_SECRET` | `openssl rand -base64 32` |
| `GRADIO_AUTH_PASSWORD` | password seguro |
| `OPENAI_API_KEY` | desde platform.openai.com |
| `MCP_AUTH_TOKEN` | string libre como Bearer token |
| `DJANGO_SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(50))"` |

### 2. Restaurar datos (si migrás desde otro servidor)

Los datos viven en bind mounts dentro del proyecto. Hay dos opciones:

**Opción A — Copiar directorios directamente (recomendado):**
```bash
scp -r usuario@origen:~/n8npozos/n8n_storage/ ./
scp -r usuario@origen:~/n8npozos/postgres_storage/ ./
scp -r usuario@origen:~/n8npozos/chroma_storage/ ./
```

**Opción B — Desde backups comprimidos:**
```bash
scp usuario@origen:~/n8npozos/backups/n8n_TIMESTAMP.tar.gz     ./backups/n8n_storage.tar.gz
scp usuario@origen:~/n8npozos/backups/postgres_TIMESTAMP.tar.gz ./backups/postgres_storage.tar.gz
scp usuario@origen:~/n8npozos/backups/chroma_TIMESTAMP.tar.gz   ./backups/chroma_storage.tar.gz

make restore
```

> **Importante:** La `N8N_ENCRYPTION_KEY` debe ser **exactamente igual** que en el servidor origen. Si cambia, todas las credenciales guardadas en n8n quedan ilegibles.

### 3. Construir imágenes y levantar

```bash
make build   # construir imágenes Docker (Django, Gradio, API)
make prod    # levantar todos los servicios
docker ps    # verificar que todos estén healthy
```

### 4. Inicializar base de datos Django

En una instalación nueva (sin datos restaurados), crear la base de datos de Django:

```bash
./scripts/init-database.sh
```

Esto crea la DB `n8n_django` en PostgreSQL. Las tablas se crean automáticamente cuando Django arranca.

### 5. Configurar nginx

```bash
make nginx-config
# Genera: <DOMAIN>.conf usando las variables del .env

sudo cp *.conf /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/<DOMAIN>.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 6. HTTPS con certbot

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d tu-dominio.com
```

### 7. Generar API Key de n8n

Una vez que n8n esté corriendo y hayas creado tu cuenta:

1. Entrá a `https://tu-dominio.com` → **Settings → API → Create API Key**
2. Copiá el token y agregalo al `.env`:
   ```
   N8N_API_KEY=tu-token-de-n8n
   ```
3. Recreá los contenedores que usan la API Key:
   ```bash
   docker compose --env-file .env -f deploy/docker-compose.yml up -d --force-recreate n8n-mcp django
   ```

### 8. Crear superusuario Django

```bash
make createsuperuser-django
# Accedé a: https://tu-dominio.com/dashboard/admin/
```

---

## Desarrollo local

### Primera vez: entorno virtual Python

Para correr Gradio o la API fuera de Docker:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # Gradio + ChromaDB
pip install -r requirements-dev.txt    # dependencias adicionales
```

> Si no usás virtualenv: `pip install -r requirements.txt` directamente.

### Levantar todos los servicios en modo desarrollo

```bash
make dev
```

El override de desarrollo (`config/development/docker-compose.override.yml`) activa:
- Puertos locales para acceder a PostgreSQL (5433) y ChromaDB (8008) desde el host
- Bind mounts de `dj/core/`, `dj/dashboard/`, `dj/audit/` y `dj/static/` en el contenedor Django
- `N8N_URL=http://n8n:5678` — Django consulta el n8n local, no producción
- `DEBUG=True` en Django y gunicorn con `--reload`

Servicios disponibles:

| Servicio | URL | Credenciales |
|---|---|---|
| n8n | http://localhost:5679 | cuenta propia |
| Django Dashboard | http://localhost:8010 | superusuario Django |
| Gradio (Docker) | http://localhost:7860 | `GRADIO_AUTH_USERNAME` / `GRADIO_AUTH_PASSWORD` del `.env` |
| API (docs) | http://localhost:8009/api/docs | — |
| n8n-MCP | http://localhost:3001/mcp | Bearer `MCP_AUTH_TOKEN` del `.env` |

### CSS — Tailwind + daisyUI

El CSS se compila desde `dj/theme/static_src/src/styles.css` → `dj/static/css/tailwind.css`.
El contenedor Django tiene bind mount de `dj/static/` — el CSS compilado llega automáticamente sin reiniciar.

```bash
make tailwind-dev    # watcher: recompila automáticamente al guardar (para desarrollo)
make tailwind-build  # compilar una vez (requerido antes de make build)
```

> Correr `make tailwind-dev` en una terminal separada mientras desarrollás templates o estilos.

### Código fuente Django con hot-reload

Los bind mounts del override sincronizan el código fuente directamente al contenedor. Cualquier cambio en settings, vistas o templates se aplica automáticamente — gunicorn detecta el cambio y recarga sin reiniciar el contenedor.

### N8N_API_KEY en desarrollo

El `N8N_API_KEY` del `.env` lo usa Django para consultar la API de n8n. En desarrollo apunta al n8n local (`http://localhost:5679`). Para generarlo:

1. Accedé a http://localhost:5679 → **Settings → API → Create API Key**
2. Actualizá `N8N_API_KEY` en `.env`
3. Recreá el contenedor Django:
   ```bash
   docker compose --env-file .env -f deploy/docker-compose.yml -f config/development/docker-compose.override.yml up -d django
   ```

### Correr Gradio fuera de Docker

```bash
source .venv/bin/activate
python src/gradio/app.py
```

> Si el contenedor Docker de Gradio ya ocupa el 7860:
> ```bash
> GRADIO_SERVER_PORT=7861 python src/gradio/app.py
> ```

### Correr la API fuera de Docker

```bash
source .venv/bin/activate
cd src/api && python main.py
```

---

## Django Dashboard

Permite monitorear y auditar las conversaciones del chatbot WhatsApp integrado con n8n.

### Funcionalidades

- **Panel principal** — estadísticas de workflows y conversaciones activas
- **Historial de chats** — conversaciones con metadatos (teléfono, cotización, ubicación)
- **Auditoría** — revisar y ajustar prompts del sistema, puntuar respuestas del bot

### Arquitectura de datos

Django **no almacena** los datos operativos — los consume en tiempo real desde la API REST de n8n:
- Historial de chats → DataTables de n8n
- Ejecuciones de workflows → API de n8n
- Auditoría de prompts → DataTables de n8n

La única base de datos propia de Django (`n8n_django`) guarda sesiones y usuarios del admin.

### Tailwind + daisyUI

- Tema: `pozo-silk` (dark, definido en `dj/theme/static_src/src/styles.css`)
- El Dockerfile compila el CSS durante el build de la imagen
- En desarrollo, `make tailwind-dev` recompila automáticamente

---

## n8n-MCP — Control de n8n desde AI IDEs

Permite a herramientas de AI (Cursor, Claude Code, etc.) crear, modificar y ejecutar workflows de n8n directamente desde el chat.

### Herramientas disponibles

| Categoría | Herramientas |
|---|---|
| Workflows | `n8n_create_workflow`, `n8n_get_workflow`, `n8n_list_workflows`, `n8n_update_full_workflow`, `n8n_update_partial_workflow`, `n8n_delete_workflow`, `n8n_validate_workflow`, `n8n_generate_workflow` |
| Ejecución | `n8n_test_workflow`, `n8n_executions`, `n8n_autofix_workflow` |
| Nodos | `search_nodes`, `get_node`, `validate_node` |
| Templates | `search_templates`, `get_template`, `n8n_deploy_template` |
| Otros | `n8n_health_check`, `n8n_workflow_versions`, `n8n_manage_datatable`, `tools_documentation` |

### Configurar en Claude Code o Cursor (modo HTTP)

**Producción:**
```json
{
  "mcpServers": {
    "n8n": {
      "type": "http",
      "url": "https://tu-dominio.com/mcp",
      "headers": { "Authorization": "Bearer <MCP_AUTH_TOKEN>" }
    }
  }
}
```

**Desarrollo local:**
```json
{
  "mcpServers": {
    "n8n": {
      "type": "http",
      "url": "http://localhost:3001/mcp",
      "headers": { "Authorization": "Bearer <MCP_AUTH_TOKEN>" }
    }
  }
}
```

### Configurar en Cursor (modo stdio, sin servidor)

```json
{
  "mcpServers": {
    "n8n-mcp": {
      "command": "npx",
      "args": ["n8n-mcp"],
      "env": {
        "MCP_MODE": "stdio",
        "LOG_LEVEL": "error",
        "DISABLE_CONSOLE_OUTPUT": "true",
        "N8N_API_URL": "https://tu-dominio.com",
        "N8N_API_KEY": "<N8N_API_KEY>"
      }
    }
  }
}
```

### Verificar

```bash
curl https://tu-dominio.com/mcp/health
# {"status":"ok","mode":"http-fixed","version":"..."}
```

---

## API — Búsqueda MMR

Expone búsqueda semántica con **Maximum Marginal Relevance** (resultados relevantes y diversos).

### `POST /api/retrievers/collections/{collection_name}/mmr`

```json
{
  "query": "texto de búsqueda",
  "k": 4,
  "fetch_k": 20,
  "lambda_mult": 0.5,
  "min_score": 0.4,
  "filters": { "campo": "valor" }
}
```

| Parámetro | Descripción | Default |
|---|---|---|
| `query` | Texto a buscar | — |
| `k` | Resultados a retornar | `4` |
| `fetch_k` | Candidatos a evaluar | `20` |
| `lambda_mult` | `0.0` = solo relevancia · `1.0` = solo diversidad | `0.5` |
| `min_score` | Score mínimo de similitud (0–1) | `0.4` |
| `filters` | Filtros sobre metadata | `null` |

Documentación interactiva: `https://tu-dominio.com/api/docs`

---

## Backup y restauración

Los datos viven en bind mounts dentro del proyecto — no se usan volúmenes Docker nombrados.

### Crear backup

```bash
make backup
# Genera en backups/:
#   n8n_TIMESTAMP.tar.gz
#   postgres_TIMESTAMP.tar.gz
#   chroma_TIMESTAMP.tar.gz
```

### Restaurar desde backup

```bash
# Renombrar con el nombre exacto esperado por el script:
mv backups/n8n_TIMESTAMP.tar.gz      backups/n8n_storage.tar.gz
mv backups/postgres_TIMESTAMP.tar.gz  backups/postgres_storage.tar.gz
mv backups/chroma_TIMESTAMP.tar.gz    backups/chroma_storage.tar.gz

make restore
```

---

## Comandos disponibles

```bash
make help                    # Ver todos los comandos disponibles

# Entornos
make dev                     # Levantar stack en modo desarrollo (con override local)
make prod                    # Levantar stack en producción
make build                   # Construir imágenes Docker
make rebuild                 # Reconstruir sin cache
make stop                    # Detener servicios

# Datos
make backup                  # Backup de datos → backups/
make restore                 # Restaurar desde backups/
make clean                   # Eliminar contenedores, imágenes y volúmenes

# Nginx
make nginx-config            # Generar config de nginx desde .env

# Logs
make logs                    # Todos los servicios
make logs-n8n
make logs-gradio
make logs-api
make logs-django

# Shells
make shell-n8n
make shell-gradio
make shell-api
make shell-django
make shell-postgres          # psql en PostgreSQL

# Django
make migrate-django          # Ejecutar migraciones
make createsuperuser-django  # Crear superusuario

# CSS
make tailwind-dev            # Watcher — recompila al guardar (desarrollo)
make tailwind-build          # Compilar una vez (antes de make build)
```

---

## Variables de entorno

Ver `.env.example` para la lista completa con descripción de cada variable.

| Variable | Descripción |
|---|---|
| `DOMAIN` | Dominio público (sin https://) |
| `N8N_PORT` | Puerto local de n8n (default: 5679) |
| `GRADIO_PORT` | Puerto local de Gradio (default: 7860) |
| `API_PORT` | Puerto local de la API (default: 8009) |
| `DJANGO_PORT` | Puerto local de Django (default: 8010) |
| `MCP_PORT` | Puerto local del MCP (default: 3001) |
| `POSTGRES_USER` | Usuario de PostgreSQL |
| `POSTGRES_PASSWORD` | Password de PostgreSQL |
| `N8N_ENCRYPTION_KEY` | Cifra credenciales en n8n — no cambiar después del primer uso |
| `N8N_USER_MANAGEMENT_JWT_SECRET` | JWT para autenticación en n8n |
| `N8N_API_KEY` | API Key generada en n8n (Settings → API) |
| `N8N_SECURE_COOKIE` | `true` en producción con HTTPS, `false` en desarrollo |
| `OPENAI_API_KEY` | Clave de OpenAI para embeddings |
| `EMBEDDING_MODEL` | Modelo de embeddings (default: `text-embedding-3-large`) |
| `GRADIO_AUTH_USERNAME` | Usuario del panel Gradio |
| `GRADIO_AUTH_PASSWORD` | Password del panel Gradio |
| `MCP_AUTH_TOKEN` | Bearer token para el servidor MCP |
| `DJANGO_SECRET_KEY` | Clave secreta de Django |
| `DJANGO_DB` | Nombre de la DB de Django (default: `n8n_django`) |

---

## Nginx

`deploy/nginx.conf.template` usa variables del `.env` sustituidas con `envsubst`.

**Routing:**
- `/` → n8n (con WebSocket)
- `/dashboard/` → Django Dashboard
- `/gradio/` → Gradio (con WebSocket)
- `/api/` → FastAPI
- `/mcp` → n8n-MCP

---

## Seguridad

- Nunca commitear `.env`
- Todos los puertos bindeados a `127.0.0.1` — solo accesibles desde nginx local
- Firewall: solo puertos 80 y 443 deben ser públicos
- Cambiar todas las passwords por defecto antes de exponer al exterior
- `N8N_ENCRYPTION_KEY` — guardarla en un lugar seguro, perderla = perder todas las credenciales de n8n
