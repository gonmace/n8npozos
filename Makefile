.PHONY: help dev prod stop clean build rebuild check-ports logs shell django tailwind backup restore nginx-config

COMPOSE     = docker compose --env-file .env -f deploy/docker-compose.yml
COMPOSE_DEV = $(COMPOSE) -f config/development/docker-compose.override.yml

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# ── Entornos ──────────────────────────────────────────────────────────────────

dev: check-ports ## Levantar dev  (bind mounts + puertos locales)
	$(COMPOSE_DEV) up -d

prod: ## Levantar producción
	@./scripts/prod.sh

stop: ## Detener  [ENV=production]
	@./scripts/stop.sh $(ENV)

# ── Debug ─────────────────────────────────────────────────────────────────────

logs: ## Logs  [SVC=n8n|django|api|gradio]
	$(COMPOSE) logs -f $(SVC)

shell: ## Shell en contenedor  SVC=django|api|gradio|n8n|postgres
	@case "$(SVC)" in \
		postgres) $(COMPOSE) exec postgres psql \
			-U $$(grep POSTGRES_USER .env | cut -d= -f2) \
			-d $$(grep POSTGRES_DB   .env | cut -d= -f2) ;; \
		n8n)      $(COMPOSE) exec n8n /bin/sh ;; \
		*)        $(COMPOSE) exec $(SVC) /bin/bash ;; \
	esac

django: ## Comando Django  CMD=migrate|createsuperuser|…
	$(COMPOSE) exec django python manage.py $(CMD)

# ── Imágenes ──────────────────────────────────────────────────────────────────

build: ## Construir imágenes  [--no-cache con rebuild]
	$(COMPOSE) build --progress=plain

rebuild: ## Reconstruir sin cache
	$(COMPOSE) build --no-cache --progress=plain

# ── Tailwind ──────────────────────────────────────────────────────────────────

tailwind: ## CSS Tailwind  [WATCH=1 para modo dev]
	@if [ "$(WATCH)" = "1" ]; then \
		cd dj/theme/static_src && npm run dev; \
	else \
		cd dj/theme/static_src && npm install && npm run build; \
	fi

# ── Datos ─────────────────────────────────────────────────────────────────────

backup: ## Backup de volúmenes
	@./scripts/backup.sh

restore: ## Restaurar desde backups/
	@./scripts/restore.sh

clean: ## Limpiar contenedores, imágenes y volúmenes
	@./scripts/clean.sh

nginx-config: ## Generar configuración nginx desde .env
	@./scripts/generate-nginx.sh

# ── Interno ───────────────────────────────────────────────────────────────────

check-ports:
	@set -a; . ./.env; set +a; \
	PORTS="$${N8N_PORT:-6001}:n8n $${GRADIO_PORT:-6002}:gradio $${API_PORT:-6003}:api $${DJANGO_PORT:-6004}:django $${MCP_PORT:-6005}:mcp"; \
	BLOCKED=""; \
	for entry in $$PORTS; do \
		port=$${entry%%:*}; svc=$${entry##*:}; \
		if ss -tlnp 2>/dev/null | grep -q ":$$port "; then \
			BLOCKED="$$BLOCKED\n  \033[31m✗\033[0m $$port ($$svc) — ocupado"; \
		else \
			printf "  \033[32m✓\033[0m $$port ($$svc) — libre\n"; \
		fi; \
	done; \
	if [ -n "$$BLOCKED" ]; then \
		printf "$$BLOCKED\n\n\033[33mSugerencia:\033[0m ajusta los puertos en .env\n"; \
		exit 1; \
	fi
