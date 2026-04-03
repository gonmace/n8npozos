.PHONY: help dev prod stop clean backup restore nginx-config logs shell-gradio shell-postgres shell-n8n tailwind-build tailwind-dev

help: ## Mostrar esta ayuda
	@echo "Comandos disponibles:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev: ## Iniciar servicios de desarrollo con override (puertos locales, bind mounts de código)
	docker compose --env-file .env -f deploy/docker-compose.yml -f config/development/docker-compose.override.yml up -d

prod: ## Iniciar entorno de producción
	@./scripts/prod.sh

stop: ## Detener servicios (usa: make stop ENV=production para producción)
	@./scripts/stop.sh $(ENV)

clean: ## Limpiar contenedores, imágenes y volúmenes
	@./scripts/clean.sh

backup: ## Crear backup de volúmenes
	@./scripts/backup.sh

restore: ## Restaurar volúmenes desde backups/
	@./scripts/restore.sh

nginx-config: ## Generar configuración de nginx desde .env
	@./scripts/generate-nginx.sh

logs: ## Ver logs de todos los servicios
	docker compose --env-file .env -f deploy/docker-compose.yml logs -f

logs-gradio: ## Ver logs de Gradio
	docker compose --env-file .env -f deploy/docker-compose.yml logs -f gradio

logs-n8n: ## Ver logs de n8n
	docker compose --env-file .env -f deploy/docker-compose.yml logs -f n8n

logs-api: ## Ver logs del microservicio API
	docker compose --env-file .env -f deploy/docker-compose.yml logs -f api

shell-gradio: ## Abrir shell en contenedor de Gradio
	docker compose --env-file .env -f deploy/docker-compose.yml exec gradio /bin/bash

shell-api: ## Abrir shell en contenedor del microservicio API
	docker compose --env-file .env -f deploy/docker-compose.yml exec api /bin/bash

shell-postgres: ## Abrir shell en contenedor de PostgreSQL
	docker compose --env-file .env -f deploy/docker-compose.yml exec postgres psql -U $$(grep POSTGRES_USER .env | cut -d '=' -f2) -d $$(grep POSTGRES_DB .env | cut -d '=' -f2)

shell-n8n: ## Abrir shell en contenedor de n8n
	docker compose --env-file .env -f deploy/docker-compose.yml exec n8n /bin/sh

logs-django: ## Ver logs del servicio Django
	docker compose --env-file .env -f deploy/docker-compose.yml logs -f django

shell-django: ## Abrir shell en contenedor de Django
	docker compose --env-file .env -f deploy/docker-compose.yml exec django /bin/bash

migrate-django: ## Ejecutar migraciones de Django
	docker compose --env-file .env -f deploy/docker-compose.yml exec django python manage.py migrate

createsuperuser-django: ## Crear superusuario Django
	docker compose --env-file .env -f deploy/docker-compose.yml exec django python manage.py createsuperuser

tailwind-build: ## Compilar CSS de Tailwind una vez (requerido antes de correr Django local)
	cd dj/theme/static_src && npm install && npm run build

tailwind-dev: ## Vigilar y recompilar CSS de Tailwind automáticamente (para dev local)
	cd dj/theme/static_src && npm run dev

build: ## Construir imágenes Docker
	docker compose --env-file .env -f deploy/docker-compose.yml build --progress=plain

rebuild: ## Reconstruir imágenes sin cache
	docker compose --env-file .env -f deploy/docker-compose.yml build --no-cache --progress=plain

