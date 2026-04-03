# Django Dashboard — Monitoreo y Auditoría

Panel web para monitorear workflows de n8n y auditar conversaciones del chatbot WhatsApp.

Acceso: `https://tu-dominio.com/dashboard/`

## Funcionalidades

### Dashboard principal (`/dashboard/`)
- Estadísticas de workflows: total, activos, inactivos
- Conteo de conversaciones totales y con cotización asignada
- Ejecuciones recientes de n8n

### Historial de chats (`/dashboard/chats/`)
- Lista de todas las conversaciones con datos del cliente: teléfono, contacto, cotización, distancia desde SCZ
- Vista detallada de una conversación con historial completo de mensajes
- Exportar conversación a Markdown

### Auditoría de prompts (`/dashboard/audit/`)
- Lista los registros de la DataTable `auditoria` de n8n
- Editar `prompt_ajuste` de cada registro
- Actualizar el system prompt directamente en el nodo del workflow de n8n
- Estadísticas: score promedio, distribución de evaluaciones (excelente/buena/aceptable/deficiente)
- Eliminar registros de la tabla

### Scripts (`/dashboard/audit/scripts/`)
- **Parsear chats**: convierte exports `.txt` de WhatsApp a `.json` estructurado en `chats/`
- **Enviar mensajes**: simula conversaciones enviando mensajes al chatbot (para testing)
- Ejecución en background con output en tiempo real y cancelación

---

## Estructura

```
dj/
├── core/
│   ├── settings.py     # Configuración Django (DB, static, sub-path)
│   ├── urls.py         # Rutas raíz: admin/, dashboard/, audit/
│   ├── wsgi.py
│   └── asgi.py
├── dashboard/
│   ├── views.py        # index, workflow_detail, chat_history
│   ├── urls.py
│   ├── n8n_service.py  # Cliente n8n API (DataTables, workflows, webhooks)
│   ├── models.py       # (vacío — datos en DataTables n8n)
│   └── templates/dashboard/
├── audit/
│   ├── views.py        # audit_index, update_prompt, run_script, etc.
│   ├── urls.py
│   ├── models.py       # (vacío — datos en DataTable auditoria n8n)
│   └── templates/audit/
├── theme/              # Tailwind CSS + daisyUI (django-tailwind)
│   └── static_src/     # package.json + tailwind.config.js
├── static/             # Archivos estáticos propios (vacío, .gitkeep)
├── manage.py
└── requirements.txt
```

---

## n8n DataTables usadas

| Tabla | ID | Campos principales |
|---|---|---|
| `pozos_clientes` | `0zB8nzU75uBn6rRp` | session_id, telefono, contacto, precio, fecha_precio, dist_from_scz |
| `pozos_state` | `mKLOfijuNXAa8MZi` | session_id, state, resumen |
| `auditoria` | `kL9BzTmpuJiuPxh6` | id, prompt_inicial, prompt_ajuste, score_global, evaluacion, ajustar_workflow, nodo_ajuste_id |

**Project ID n8n:** `D5S4DzsCuzzjBHo5`

El historial de mensajes de cada sesión se obtiene vía webhook:
`GET /webhook/get_session_history?sessionId=<id>`

---

## Variables de entorno relevantes

| Variable | Descripción |
|---|---|
| `N8N_API_KEY` | API Key de n8n — requerida para leer DataTables y workflows |
| `N8N_URL` o `DOMAIN` | URL base de n8n (ej. `https://n8npozos.magoreal.com`) |
| `DJANGO_SECRET_KEY` | Clave secreta Django — generar con `secrets.token_urlsafe(50)` |
| `DJANGO_DB` | Nombre de la DB PostgreSQL (`n8n_django`) |
| `N8N_WORKFLOW_PROMPT_ID` | ID del workflow cuyo nodo de system prompt se puede actualizar |
| `N8N_WEBHOOK_UPDATE_AUDIT_PROMPT` | Webhook fallback para actualizar DataTable si la API falla |
| `N8N_WEBHOOK_UPDATE_PROMPT_NODE` | Webhook fallback para actualizar nodo si la API falla |

---

## Despliegue

Django corre en Docker, se levanta con el stack principal:

```bash
make prod   # incluye Django automáticamente
```

Las migraciones se ejecutan automáticamente al arrancar el contenedor (`docker-entrypoint.sh`).

Para crear el superusuario del admin:
```bash
make createsuperuser-django
# Admin: https://tu-dominio.com/dashboard/admin/
```

---

## Desarrollo local

```bash
# 1. Levantar PostgreSQL y n8n en Docker
make dev

# 2. Variables de entorno para Django local (crear dj/.env o usar el .env de la raíz)
# DJANGO_DB=n8n_django, POSTGRES_PASSWORD=..., N8N_API_KEY=...

# 3. Correr Django
cd dj
python manage.py migrate
python manage.py runserver
```

Para desarrollo de Tailwind (hot-reload CSS):
```bash
make tailwind-dev
# o directamente:
cd dj/theme/static_src && npm run dev
```

> Primera vez: `make tailwind-build` para generar el CSS antes de correr Django.

---

## Sub-path `/dashboard/`

Django está configurado para servir bajo `/dashboard/` via nginx:

- `FORCE_SCRIPT_NAME = '/dashboard'` — todos los `{% url %}` y redirects usan el prefijo
- `STATIC_URL = '/dashboard/static/'` — whitenoise sirve los estáticos con el prefijo correcto
- Nginx hace `proxy_pass http://127.0.0.1:8010/;` (trailing slash = strip del prefijo antes de reenviar a gunicorn)
