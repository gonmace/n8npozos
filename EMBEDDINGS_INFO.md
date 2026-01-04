# Información sobre Modelos de Embedding

## Estado Actual

El proyecto está configurado para usar **OpenAI text-embedding-3-large** como modelo de embedding.

### Configuración Actual

- **Modelo**: `text-embedding-3-large` (OpenAI)
- **Dimensión**: 3072 (configurable)
- **Idioma**: Multilingüe (excelente para español e inglés)
- **Requisito**: API Key de OpenAI

### Configuración en el Código

En `src/gradio/app.py`:

```python
from chromadb.utils import embedding_functions

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")

embedding_function = embedding_functions.OpenAIEmbeddingFunction(
    api_key=OPENAI_API_KEY,
    model_name=EMBEDDING_MODEL
)

collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=embedding_function
)
```

### Fallback

Si `OPENAI_API_KEY` no está configurada, el sistema usa el modelo por defecto de ChromaDB:
- **Modelo**: `all-MiniLM-L6-v2` de Sentence Transformers
- **Dimensión**: 384

## Cómo Verificar el Modelo Actual

Para verificar qué modelo está usando tu colección:

```python
import chromadb

client = chromadb.HttpClient(host="localhost", port=8008)
collection = client.get_collection("pozos")

# Ver metadatos de la colección
print(collection.metadata)
```

## Cómo Cambiar el Modelo de Embedding

Si quieres usar un modelo diferente, puedes especificarlo al crear la colección:

### Opción 1: Usar Sentence Transformers (Recomendado)

```python
from chromadb.utils import embedding_functions

# Usar un modelo específico de Sentence Transformers
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"  # Mejor para español
)

collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=sentence_transformer_ef
)
```

### Opción 2: Usar OpenAI (Requiere API Key)

```python
from chromadb.utils import embedding_functions

openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key="tu-api-key",
    model_name="text-embedding-ada-002"
)

collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=openai_ef
)
```

### Opción 3: Usar un Modelo Personalizado

```python
from chromadb.utils import embedding_functions

# Modelo específico para español
spanish_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=spanish_ef
)
```

## Modelos Recomendados para Español

1. **`paraphrase-multilingual-MiniLM-L12-v2`**
   - Dimensión: 384
   - Buen rendimiento para español
   - Tamaño: ~420MB

2. **`paraphrase-multilingual-mpnet-base-v2`**
   - Dimensión: 768
   - Mejor calidad, más lento
   - Tamaño: ~420MB

3. **`distiluse-base-multilingual-cased-v2`**
   - Dimensión: 512
   - Optimizado para múltiples idiomas
   - Tamaño: ~130MB

## Importante

⚠️ **Si cambias el modelo de embedding, necesitas recrear la colección** porque los embeddings existentes fueron creados con el modelo anterior y no serán compatibles.

Para cambiar el modelo:

1. Exportar los datos existentes (textos y metadatos)
2. Eliminar la colección actual
3. Crear nueva colección con el nuevo modelo
4. Re-importar los datos (se crearán nuevos embeddings)

## Dónde Configurarlo

El modelo se configura en `src/gradio/app.py` en la línea donde se crea la colección:

```python
# Línea actual (sin modelo específico):
collection = client.get_or_create_collection(COLLECTION_NAME)

# Con modelo específico:
from chromadb.utils import embedding_functions
ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)
collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=ef
)
```

