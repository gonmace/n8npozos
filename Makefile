.PHONY: help dev prod stop clean backup logs shell-gradio shell-postgres shell-n8n

help: ## Mostrar esta ayuda
	@echo "Comandos disponibles:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev: ## Iniciar entorno de desarrollo LOCAL (Gradio sin Docker)
	@./scripts/dev-local.sh

dev-api: ## Iniciar API en desarrollo LOCAL (sin Docker)
	@./scripts/dev-api-local.sh

dev-docker: ## Iniciar entorno de desarrollo CON Docker (todo containerizado)
	@./scripts/dev-docker.sh

dev-services: ## Iniciar solo servicios (PostgreSQL, ChromaDB, n8n) para desarrollo local
	@./scripts/dev-services.sh

prod: ## Iniciar entorno de producción
	@./scripts/prod.sh

stop: ## Detener servicios (usa: make stop ENV=production para producción)
	@./scripts/stop.sh $(ENV)

clean: ## Limpiar contenedores, imágenes y volúmenes
	@./scripts/clean.sh

backup: ## Crear backup de volúmenes
	@./scripts/backup.sh

logs: ## Ver logs de todos los servicios
	docker-compose --env-file .env -f deploy/docker-compose.yml logs -f

logs-gradio: ## Ver logs de Gradio
	docker-compose --env-file .env -f deploy/docker-compose.yml logs -f gradio

logs-n8n: ## Ver logs de n8n
	docker-compose --env-file .env -f deploy/docker-compose.yml logs -f n8n

logs-api: ## Ver logs del microservicio API
	docker-compose --env-file .env -f deploy/docker-compose.yml logs -f api

shell-gradio: ## Abrir shell en contenedor de Gradio
	docker-compose --env-file .env -f deploy/docker-compose.yml exec gradio /bin/bash

shell-api: ## Abrir shell en contenedor del microservicio API
	docker-compose --env-file .env -f deploy/docker-compose.yml exec api /bin/bash

shell-postgres: ## Abrir shell en contenedor de PostgreSQL
	docker-compose --env-file .env -f deploy/docker-compose.yml exec postgres psql -U $$(grep POSTGRES_USER .env | cut -d '=' -f2) -d $$(grep POSTGRES_DB .env | cut -d '=' -f2)

shell-n8n: ## Abrir shell en contenedor de n8n
	docker-compose --env-file .env -f deploy/docker-compose.yml exec n8n /bin/sh

build: ## Construir imágenes Docker
	docker-compose --env-file .env -f deploy/docker-compose.yml build --progress=plain

rebuild: ## Reconstruir imágenes sin cache
	docker-compose --env-file .env -f deploy/docker-compose.yml build --no-cache --progress=plain

