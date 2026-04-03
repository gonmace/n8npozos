# API — Búsqueda MMR

Microservicio FastAPI que expone búsqueda semántica con Maximum Marginal Relevance sobre ChromaDB.

## Endpoints

- `GET /health` — Health check
- `POST /retrievers/collections/{collection_name}/mmr` — Búsqueda MMR

Documentación interactiva disponible en `/docs` (Swagger UI).

## Desarrollo local

```bash
# 1. Levantar servicios (PostgreSQL, ChromaDB, n8n)
make dev

# 2. Activar entorno virtual e instalar dependencias
python -m .venv .venv && source .venv/bin/activate
pip install -r src/api/requirements.txt

# 3. Correr el API con hot-reload
cd src/api && python main.py
```

## Ejemplo — búsqueda MMR

```bash
curl -X POST "http://localhost:8009/retrievers/collections/pozos/mmr" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Warnes",
    "k": 4,
    "fetch_k": 20,
    "lambda_mult": 0.5,
    "min_score": 0.4
  }'
```
