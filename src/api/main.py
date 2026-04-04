from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from typing import Optional, Dict, Any
import uvicorn
from chromadb_client import mmr_search

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8009"))
API_ROOT_PATH = os.getenv("API_ROOT_PATH", "")
ENV = os.getenv("ENV", "production")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

app = FastAPI(
    title="API",
    version="1.0.0",
    root_path=API_ROOT_PATH,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "healthy"}


class DocumentCreate(BaseModel):
    text: str
    categoria: Optional[str] = None
    source: Optional[str] = None
    doc_id: Optional[str] = None


class DocumentUpdate(BaseModel):
    text: str
    categoria: Optional[str] = None
    source: Optional[str] = None


@app.get("/collections/{collection_name}/documents")
async def list_documents(collection_name: str):
    try:
        from chromadb_client import get_all_vectors
        result = get_all_vectors(collection_name)
        docs = []
        for i, doc_id in enumerate(result.get("ids", [])):
            meta = result["metadatas"][i] if i < len(result.get("metadatas", [])) else {}
            docs.append({
                "id": doc_id,
                "document": result["documents"][i] if i < len(result.get("documents", [])) else "",
                "metadata": meta or {},
            })
        return {"collection": collection_name, "count": len(docs), "documents": docs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/collections/{collection_name}/documents", status_code=201)
async def create_document_endpoint(collection_name: str, request: DocumentCreate):
    try:
        from chromadb_client import create_document
        metadata = {}
        if request.categoria:
            metadata["categoria"] = request.categoria
        if request.source:
            metadata["source"] = request.source
        doc_id = create_document(collection_name, request.text, metadata or None, request.doc_id)
        return {"id": doc_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collections/{collection_name}/documents/{doc_id}")
async def get_document_endpoint(collection_name: str, doc_id: str):
    try:
        from chromadb_client import get_document
        return get_document(collection_name, doc_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.put("/collections/{collection_name}/documents/{doc_id}")
async def update_document_endpoint(collection_name: str, doc_id: str, request: DocumentUpdate):
    try:
        from chromadb_client import update_document
        metadata = {}
        if request.categoria:
            metadata["categoria"] = request.categoria
        if request.source:
            metadata["source"] = request.source
        update_document(collection_name, doc_id, request.text, metadata or None)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/collections/{collection_name}/documents/{doc_id}")
async def delete_document_endpoint(collection_name: str, doc_id: str):
    try:
        from chromadb_client import delete_document
        delete_document(collection_name, doc_id)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class MMRRetrieveRequest(BaseModel):
    query: str
    k: int = 4
    fetch_k: int = 20
    lambda_mult: float = 0.5
    filters: Optional[Dict[str, Any]] = None
    min_score: float = 0.4


@app.post("/retrievers/collections/{collection_name}/mmr")
async def post_mmr_retrieve(collection_name: str, request: MMRRetrieveRequest):
    """Maximum Marginal Relevance search — relevancia con diversidad de resultados."""
    try:
        cleaned_filters = None
        if request.filters:
            cleaned_filters = {
                k: v for k, v in request.filters.items()
                if not k.startswith("additionalProp") and v is not None and v != ""
                and (not isinstance(v, dict) or v)
            }

        result = mmr_search(
            collection_name=collection_name,
            query=request.query,
            k=request.k,
            fetch_k=request.fetch_k,
            lambda_mult=request.lambda_mult,
            filters=cleaned_filters,
            min_score=request.min_score,
        )

        return {
            "collection": collection_name,
            "query": request.query,
            "results": result.get("results", []),
            "count": result.get("count", 0),
            "search_type": result.get("search_type", "mmr_langchain"),
            "min_score": result.get("min_score", request.min_score),
        }
    except Exception as e:
        if DEBUG:
            import traceback
            traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=DEBUG,
        log_level="debug" if DEBUG else "info",
    )
