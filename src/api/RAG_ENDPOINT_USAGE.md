# Endpoint POST para RAG Retriever con Umbrales

## Endpoint

```
POST /rag/collections/{collection_name}/retrieve
```

## Descripción

Recupera documentos usando el RAG Retriever con evaluación de umbrales de similitud. Evalúa automáticamente si los documentos recuperados son suficientemente relevantes antes de usarlos en RAG.

## Parámetros de Path

- `collection_name`: Nombre de la colección en ChromaDB (ej: "pozos")

## Body (JSON)

```json
{
  "query": "Montero",
  "strategy": "hybrid",
  "top_k": 5,
  "similarity_threshold_mode": "relative",
  "similarity_threshold": 0.5,
  "min_documents": 1,
  "dense_weight": 0.7,
  "sparse_weight": 0.3,
  "filters": null
}
```

### Parámetros del Body

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `query` | string | **requerido** | Consulta de búsqueda |
| `strategy` | string | `"hybrid"` | Estrategia: `"hybrid"`, `"dense"`, `"sparse"`, `"ensemble"` |
| `top_k` | integer | `5` | Número de documentos a recuperar |
| `similarity_threshold_mode` | string | `"relative"` | Modo: `"relative"`, `"absolute"`, `"percentile"` |
| `similarity_threshold` | float | `0.5` | Valor del umbral según el modo |
| `min_documents` | integer | `1` | Mínimo de documentos válidos requeridos |
| `dense_weight` | float | `0.7` | Peso para búsqueda densa (solo hybrid) |
| `sparse_weight` | float | `0.3` | Peso para búsqueda sparse (solo hybrid) |
| `filters` | object | `null` | Filtros opcionales por metadatos |

## Respuesta

```json
{
  "collection": "pozos",
  "query": "Montero",
  "strategy": "hybrid",
  "documents": [
    {
      "id": "fc953d10-c65f-4c93-afce-91b502b6a9ce",
      "document": "El servicio se brinda en la ciudad de Santa Cruz...",
      "score": 0.016393,
      "metadata": null
    }
  ],
  "evaluation": {
    "is_valid": true,
    "total_retrieved": 6,
    "filtered_count": 1,
    "max_score": 0.016393,
    "min_score": 0.016393,
    "threshold_used": 0.008197,
    "threshold_mode": "relative"
  },
  "count": 1
}
```

### Campos de Evaluación

- `is_valid`: `true` si hay documentos suficientemente relevantes
- `total_retrieved`: Total de documentos recuperados antes del filtro
- `filtered_count`: Documentos que pasan el umbral
- `max_score`: Score máximo encontrado
- `min_score`: Score mínimo de documentos filtrados
- `threshold_used`: Umbral aplicado
- `threshold_mode`: Modo de umbral usado

## Ejemplos de Uso

### Ejemplo 1: Búsqueda básica con umbral relativo

```bash
curl -X POST "http://localhost:8009/rag/collections/pozos/retrieve" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Montero",
    "strategy": "hybrid",
    "top_k": 5,
    "similarity_threshold_mode": "relative",
    "similarity_threshold": 0.5
  }'
```

### Ejemplo 2: Búsqueda estricta (80% del máximo)

```bash
curl -X POST "http://localhost:8009/rag/collections/pozos/retrieve" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Montero",
    "strategy": "hybrid",
    "top_k": 10,
    "similarity_threshold_mode": "relative",
    "similarity_threshold": 0.8,
    "min_documents": 2
  }'
```

### Ejemplo 3: Búsqueda con umbral absoluto

```bash
curl -X POST "http://localhost:8009/rag/collections/pozos/retrieve" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "servicios",
    "strategy": "sparse",
    "top_k": 5,
    "similarity_threshold_mode": "absolute",
    "similarity_threshold": 0.01
  }'
```

### Ejemplo 4: Solo búsqueda semántica (dense)

```bash
curl -X POST "http://localhost:8009/rag/collections/pozos/retrieve" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "¿Dónde atienden?",
    "strategy": "dense",
    "top_k": 5,
    "similarity_threshold_mode": "relative",
    "similarity_threshold": 0.5
  }'
```

### Ejemplo 5: Con filtros

```bash
curl -X POST "http://localhost:8009/rag/collections/pozos/retrieve" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "servicios",
    "strategy": "hybrid",
    "top_k": 5,
    "similarity_threshold_mode": "relative",
    "similarity_threshold": 0.5,
    "filters": {
      "categoria": "servicios"
    }
  }'
```

## Interpretación de Resultados

### Caso 1: Documentos Válidos (`is_valid: true`)

```json
{
  "evaluation": {
    "is_valid": true,
    "filtered_count": 3
  }
}
```

**Acción**: ✅ Usar estos documentos para generar respuesta RAG

### Caso 2: Sin Documentos Válidos (`is_valid: false`)

```json
{
  "evaluation": {
    "is_valid": false,
    "total_retrieved": 5,
    "filtered_count": 0,
    "max_score": 0.005,
    "threshold_used": 0.01
  }
}
```

**Acción**: ❌ NO usar para RAG - responder que no hay información suficientemente relevante

## Modos de Umbral

### 1. Relative (Relativo) - Recomendado

- **Valor**: Porcentaje del score máximo (0.0 - 1.0)
- **Ejemplo**: `0.5` = 50% del score máximo
- **Ventaja**: Se adapta automáticamente a cada consulta

### 2. Absolute (Absoluto)

- **Valor**: Score mínimo fijo
- **Ejemplo**: `0.01` = score mínimo de 0.01
- **Ventaja**: Control preciso, requiere calibración

### 3. Percentile (Percentil)

- **Valor**: Percentil de scores (0.0 - 1.0)
- **Ejemplo**: `0.75` = percentil 75
- **Ventaja**: Siempre toma los mejores documentos

## Estrategias de Búsqueda

| Estrategia | Descripción | Cuándo Usar |
|------------|-------------|-------------|
| `hybrid` | Combina dense + sparse con RRF | **Recomendado** - Casos generales |
| `dense` | Solo búsqueda semántica | Consultas conceptuales |
| `sparse` | Solo búsqueda por keywords | Términos exactos, nombres propios |
| `ensemble` | Máxima cobertura | Cuando necesitas todos los documentos posibles |

## Flujo de Decisión RAG

```python
# 1. Llamar al endpoint
response = requests.post(
    "http://localhost:8009/rag/collections/pozos/retrieve",
    json={
        "query": "Montero",
        "similarity_threshold_mode": "relative",
        "similarity_threshold": 0.5
    }
)

# 2. Evaluar si hay documentos válidos
if response.json()["evaluation"]["is_valid"]:
    # ✅ Usar documentos para RAG
    documents = response.json()["documents"]
    # Generar respuesta con LLM usando estos documentos
else:
    # ❌ No usar para RAG
    # Responder que no hay información suficientemente relevante
    pass
```

## Swagger UI

Puedes probar el endpoint directamente en:
```
http://localhost:8009/docs#/default/post_rag_retrieve_rag_collections__collection_name__retrieve_post
```

