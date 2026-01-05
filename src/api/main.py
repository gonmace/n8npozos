"""
Microservicio API de ejemplo
Puedes usar FastAPI, Flask, o cualquier framework de tu elección
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from typing import Optional, List, Dict, Any
import uvicorn
from chromadb_client import (
    get_all_vectors,
    get_vectors_by_ids,
    list_collections,
    get_collection_info,
    mmr_search
)

# Configuración desde variables de entorno
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8009"))
ENV = os.getenv("ENV", "production")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Crear aplicación FastAPI
app = FastAPI(
    title="Microservicio API",
    description="Microservicio de ejemplo para el proyecto",
    version="1.0.0"
)

# Configurar CORS si es necesario
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especifica los orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos Pydantic
class Item(BaseModel):
    name: str
    description: Optional[str] = None
    price: float

class ItemResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    price: float


# Base de datos en memoria (en producción usarías PostgreSQL, MongoDB, etc.)
items_db = []
next_id = 1

@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "service": "Microservicio API",
        "version": "1.0.0",
        "status": "running",
        "environment": ENV
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.get("/items", response_model=List[ItemResponse])
async def get_items():
    """Obtener todos los items"""
    return items_db

@app.get("/items/{item_id}", response_model=ItemResponse)
async def get_item(item_id: int):
    """Obtener un item por ID"""
    for item in items_db:
        if item["id"] == item_id:
            return item
    raise HTTPException(status_code=404, detail="Item not found")

@app.post("/items", response_model=ItemResponse, status_code=201)
async def create_item(item: Item):
    """Crear un nuevo item"""
    global next_id
    new_item = {
        "id": next_id,
        "name": item.name,
        "description": item.description,
        "price": item.price
    }
    items_db.append(new_item)
    next_id += 1
    return new_item

@app.put("/items/{item_id}", response_model=ItemResponse)
async def update_item(item_id: int, item: Item):
    """Actualizar un item existente"""
    for i, existing_item in enumerate(items_db):
        if existing_item["id"] == item_id:
            updated_item = {
                "id": item_id,
                "name": item.name,
                "description": item.description,
                "price": item.price
            }
            items_db[i] = updated_item
            return updated_item
    raise HTTPException(status_code=404, detail="Item not found")

@app.delete("/items/{item_id}", status_code=204)
async def delete_item(item_id: int):
    """Eliminar un item"""
    for i, item in enumerate(items_db):
        if item["id"] == item_id:
            items_db.pop(i)
            return None
    raise HTTPException(status_code=404, detail="Item not found")

# ==================== Endpoints de ChromaDB ====================

@app.get("/chroma/collections")
async def list_chroma_collections():
    """Listar todas las colecciones disponibles en ChromaDB"""
    try:
        collections = list_collections()
        return {
            "collections": collections,
            "count": len(collections)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chroma/collections/{collection_name}")
async def get_chroma_collection_vectors(
    collection_name: str,
    include_embeddings: bool = Query(False, description="Incluir vectores de embedding (puede ser grande)"),
    ids: Optional[List[str]] = Query(None, description="IDs específicos a obtener (opcional)")
):
    """
    Obtener todos los vectores de una colección específica de ChromaDB
    
    Args:
        collection_name: Nombre de la colección
        include_embeddings: Si True, incluye los vectores de embedding
        ids: Lista opcional de IDs específicos a obtener
        
    Returns:
        Dict con todos los vectores de la colección
    """
    try:
        if ids:
            # Obtener vectores específicos por IDs
            result = get_vectors_by_ids(
                collection_name=collection_name,
                ids=ids,
                include_embeddings=include_embeddings
            )
        else:
            # Obtener todos los vectores de la colección
            result = get_all_vectors(
                collection_name=collection_name,
                include_embeddings=include_embeddings
            )
        
        return result
    except Exception as e:
        error_msg = str(e)
        # Log del error para debugging
        import traceback
        if DEBUG:
            print(f"Error en get_chroma_collection_vectors: {error_msg}")
            traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_msg)


@app.get("/chroma/collections/{collection_name}/info")
async def get_chroma_collection_info(collection_name: str):
    """
    Obtener información sobre una colección (count, metadata, etc.)
    
    Args:
        collection_name: Nombre de la colección
        
    Returns:
        Dict con información de la colección
    """
    try:
        info = get_collection_info(collection_name)
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class MMRRetrieveRequest(BaseModel):
    query: str  # Query única para búsqueda MMR
    k: int = 4  # Número final de documentos a retornar
    fetch_k: int = 20  # Número de documentos candidatos a recuperar inicialmente
    lambda_mult: float = 0.5  # Factor de diversidad (0.0 = solo relevancia, 1.0 = solo diversidad)
    filters: Optional[Dict[str, Any]] = None
    min_score: float = 0.4  # Score mínimo de similitud para incluir un documento


@app.post("/retrievers/collections/{collection_name}/mmr")
async def post_mmr_retrieve(
    collection_name: str,
    request: MMRRetrieveRequest
):
    """
    Maximum Marginal Relevance (MMR) Retrieval usando LangChain
    
    MMR busca maximizar la relevancia mientras minimiza la redundancia entre documentos.
    Selecciona documentos que son relevantes al query pero diversos entre sí.
    Solo retorna documentos con similarity_score >= min_score.
    
    Args:
        collection_name: Nombre de la colección
        request: Request con query, k, fetch_k, lambda_mult, min_score y filtros opcionales
        
    Returns:
        Dict con resultados de la búsqueda MMR filtrados por min_score
    """
    try:
        # Clean filters if provided
        cleaned_filters = None
        if request.filters:
            cleaned_filters = {}
            for key, value in request.filters.items():
                # Remove Swagger UI's additionalProp keys
                if key.startswith("additionalProp"):
                    continue
                # Remove empty values
                if value is not None and value != "":
                    if isinstance(value, dict):
                        # Remove empty dictionaries
                        if value:
                            cleaned_filters[key] = value
                    else:
                        cleaned_filters[key] = value
        
        result = mmr_search(
            collection_name=collection_name,
            query=request.query,
            k=request.k,
            fetch_k=request.fetch_k,
            lambda_mult=request.lambda_mult,
            filters=cleaned_filters,
            min_score=request.min_score
        )
        
        return {
            "collection": collection_name,
            "query": request.query,
            "results": result.get("results", []),
            "count": result.get("count", 0),
            "search_type": result.get("search_type", "mmr_langchain"),
            "min_score": result.get("min_score", request.min_score)
        }
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error en MMR retrieve: {error_msg}")
        if DEBUG:
            import traceback
            traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error en MMR retrieve: {error_msg}")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=DEBUG,
        log_level="debug" if DEBUG else "info"
    )

