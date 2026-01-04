"""
Cliente para interactuar con ChromaDB usando LangChain
Proporciona funciones para obtener vectores y documentos de colecciones
"""
import os
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Optional, Any
import numpy as np
from langchain_community.vectorstores import Chroma as LangChainChroma
from langchain_openai import OpenAIEmbeddings

# Configuración desde variables de entorno
# Detectar si estamos en Docker o desarrollo local
if os.getenv("CHROMA_HOST"):
    CHROMA_HOST = os.getenv("CHROMA_HOST")
else:
    # Si estamos en Docker (archivo /proc/1/cgroup existe y contiene docker)
    try:
        with open("/proc/1/cgroup", "r") as f:
            if "docker" in f.read():
                CHROMA_HOST = "chroma"  # Nombre del servicio Docker
            else:
                CHROMA_HOST = "localhost"  # Desarrollo local
    except:
        CHROMA_HOST = "localhost"  # Por defecto localhost

# Puerto: en desarrollo local con Docker, usar 8008 (puerto mapeado)
# En Docker, usar 8000 (puerto interno)
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8008" if CHROMA_HOST == "localhost" else "8000"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")

# Inicializar función de embedding de OpenAI si está disponible
embedding_function = None
if OPENAI_API_KEY:
    try:
        embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=OPENAI_API_KEY,
            model_name=EMBEDDING_MODEL
        )
    except Exception as e:
        print(f"⚠️  No se pudo inicializar OpenAI embedding function: {e}")

# Inicializar cliente de ChromaDB (lazy initialization con reintentos)
_client_instance = None
_last_init_attempt = None

def _get_client():
    """
    Obtener o inicializar el cliente de ChromaDB (lazy initialization con reintentos)
    Reintenta la conexión si falló anteriormente (útil si ChromaDB se inicia después)
    """
    global _client_instance, _last_init_attempt
    import time
    
    # Si ya tenemos un cliente válido, retornarlo
    if _client_instance is not None:
        return _client_instance
    
    # Si intentamos hace menos de 5 segundos, no reintentar (evitar spam)
    current_time = time.time()
    if _last_init_attempt is not None and (current_time - _last_init_attempt) < 5:
        return None
    
    _last_init_attempt = current_time
    
    try:
        _client_instance = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        # Verificar conexión haciendo una operación simple
        # Nota: heartbeat() puede fallar con API v1 deprecada, usar list_collections() en su lugar
        try:
            _client_instance.list_collections()
            print(f"✅ Conectado a ChromaDB en {CHROMA_HOST}:{CHROMA_PORT}")
        except Exception as list_error:
            # Si list_collections falla, intentar heartbeat como último recurso
            try:
                _client_instance.heartbeat()
                print(f"✅ Conectado a ChromaDB en {CHROMA_HOST}:{CHROMA_PORT}")
            except Exception:
                # Si ambos fallan, aún así mantener el cliente (puede funcionar para operaciones básicas)
                print(f"⚠️  Advertencia: No se pudo verificar conexión a ChromaDB, pero el cliente se creó")
                print(f"   Se intentará usar el cliente de todas formas")
        return _client_instance
    except Exception as e:
        # No imprimir error en cada intento para evitar spam
        # Solo imprimir si es el primer intento o si pasó suficiente tiempo
        if _last_init_attempt == current_time or (current_time - _last_init_attempt) > 30:
            print(f"⚠️  No se pudo crear cliente de ChromaDB en {CHROMA_HOST}:{CHROMA_PORT}")
            print(f"   Error: {str(e)}")
            print(f"   Asegúrate de que ChromaDB esté corriendo")
            print(f"   En desarrollo local, ejecuta: make dev-services")
        _client_instance = None
        return None

# Inicializar cliente al importar el módulo
client = _get_client()


def get_collection(collection_name: str):
    """
    Obtener o crear una colección en ChromaDB
    
    Args:
        collection_name: Nombre de la colección
        
    Returns:
        Collection object de ChromaDB
        
    Raises:
        Exception: Si no se puede conectar a ChromaDB
    """
    client_instance = _get_client()
    if client_instance is None:
        raise Exception(
            f"ChromaDB no está disponible. "
            f"Asegúrate de que ChromaDB esté corriendo en {CHROMA_HOST}:{CHROMA_PORT}. "
            f"En desarrollo local, ejecuta: make dev-services"
        )
    
    try:
        if embedding_function:
            collection = client_instance.get_or_create_collection(
                name=collection_name,
                embedding_function=embedding_function
            )
        else:
            collection = client_instance.get_or_create_collection(name=collection_name)
        return collection
    except ValueError as ve:
        # Si hay conflicto de embedding function, eliminar y crear nueva
        if "embedding function conflict" in str(ve).lower():
            try:
                client_instance.delete_collection(name=collection_name)
                if embedding_function:
                    collection = client_instance.get_or_create_collection(
                        name=collection_name,
                        embedding_function=embedding_function
                    )
                else:
                    collection = client_instance.get_or_create_collection(name=collection_name)
                return collection
            except Exception as e:
                raise Exception(f"Error al recrear colección: {e}")
        raise


def get_all_vectors(collection_name: str, include_embeddings: bool = False) -> Dict[str, Any]:
    """
    Obtener todos los vectores (embeddings) de una colección específica
    
    Args:
        collection_name: Nombre de la colección
        include_embeddings: Si True, incluye los vectores de embedding (puede ser grande)
        
    Returns:
        Dict con la siguiente estructura:
        {
            "collection": str,
            "count": int,
            "ids": List[str],
            "documents": List[str],
            "metadatas": List[Dict],
            "embeddings": List[List[float]] (solo si include_embeddings=True)
        }
        
    Raises:
        Exception: Si hay error al obtener los datos
    """
    client_instance = _get_client()
    if client_instance is None:
        raise Exception(
            f"ChromaDB no está disponible. "
            f"Asegúrate de que ChromaDB esté corriendo en {CHROMA_HOST}:{CHROMA_PORT}. "
            f"En desarrollo local, ejecuta: make dev-services"
        )
    
    try:
        collection = get_collection(collection_name)
        
        # Obtener todos los datos de la colección
        # Usar get() sin filtros para obtener todo
        result = collection.get(
            include=["documents", "metadatas", "embeddings"] if include_embeddings else ["documents", "metadatas"]
        )
        
        # Convertir embeddings a listas de Python si existen
        embeddings = None
        if include_embeddings:
            emb_data = result.get("embeddings")
            # Verificar que emb_data existe y no es None antes de usar en contexto booleano
            if emb_data is not None:
                embeddings = []
                for emb in emb_data:
                    # Convertir numpy arrays o cualquier tipo a lista de Python
                    if isinstance(emb, np.ndarray):
                        embeddings.append(emb.tolist())
                    elif isinstance(emb, (list, tuple)):
                        # Asegurar que todos los elementos sean tipos básicos de Python
                        try:
                            embeddings.append([float(x) for x in emb])
                        except (TypeError, ValueError):
                            # Si hay arrays anidados, convertir recursivamente
                            embeddings.append([float(x.item()) if isinstance(x, np.ndarray) else float(x) for x in emb])
                    else:
                        try:
                            embeddings.append([float(x) for x in list(emb)])
                        except (TypeError, ValueError):
                            embeddings.append(list(emb))
        
        return {
            "collection": collection_name,
            "count": len(result["ids"]) if result["ids"] else 0,
            "ids": result["ids"] or [],
            "documents": result["documents"] or [],
            "metadatas": result["metadatas"] or [],
            "embeddings": embeddings
        }
    except Exception as e:
        error_msg = str(e)
        if "ChromaDB no está disponible" in error_msg:
            raise Exception(error_msg)
        raise Exception(f"Error al obtener vectores de la colección '{collection_name}': {error_msg}")


def get_vectors_by_ids(collection_name: str, ids: List[str], include_embeddings: bool = False) -> Dict[str, Any]:
    """
    Obtener vectores específicos por sus IDs
    
    Args:
        collection_name: Nombre de la colección
        ids: Lista de IDs a obtener
        include_embeddings: Si True, incluye los vectores de embedding
        
    Returns:
        Dict con los vectores solicitados
    """
    client_instance = _get_client()
    if client_instance is None:
        raise Exception(
            f"ChromaDB no está disponible. "
            f"Asegúrate de que ChromaDB esté corriendo en {CHROMA_HOST}:{CHROMA_PORT}. "
            f"En desarrollo local, ejecuta: make dev-services"
        )
    
    try:
        collection = get_collection(collection_name)
        
        result = collection.get(
            ids=ids,
            include=["documents", "metadatas", "embeddings"] if include_embeddings else ["documents", "metadatas"]
        )
        
        # Convertir embeddings a listas de Python si existen
        embeddings = None
        if include_embeddings:
            emb_data = result.get("embeddings")
            # Verificar que emb_data existe y no es None antes de usar en contexto booleano
            if emb_data is not None:
                embeddings = []
                for emb in emb_data:
                    # Convertir numpy arrays o cualquier tipo a lista de Python
                    if isinstance(emb, np.ndarray):
                        embeddings.append(emb.tolist())
                    elif isinstance(emb, (list, tuple)):
                        # Asegurar que todos los elementos sean tipos básicos de Python
                        try:
                            embeddings.append([float(x) for x in emb])
                        except (TypeError, ValueError):
                            # Si hay arrays anidados, convertir recursivamente
                            embeddings.append([float(x.item()) if isinstance(x, np.ndarray) else float(x) for x in emb])
                    else:
                        try:
                            embeddings.append([float(x) for x in list(emb)])
                        except (TypeError, ValueError):
                            embeddings.append(list(emb))
        
        return {
            "collection": collection_name,
            "count": len(result["ids"]) if result["ids"] else 0,
            "ids": result["ids"] or [],
            "documents": result["documents"] or [],
            "metadatas": result["metadatas"] or [],
            "embeddings": embeddings
        }
    except Exception as e:
        error_msg = str(e)
        if "ChromaDB no está disponible" in error_msg:
            raise Exception(error_msg)
        raise Exception(f"Error al obtener vectores por IDs: {error_msg}")


def list_collections() -> List[str]:
    """
    Listar todas las colecciones disponibles en ChromaDB
    
    Returns:
        Lista de nombres de colecciones
    """
    client_instance = _get_client()
    if client_instance is None:
        raise Exception(
            f"ChromaDB no está disponible. "
            f"Asegúrate de que ChromaDB esté corriendo en {CHROMA_HOST}:{CHROMA_PORT}. "
            f"En desarrollo local, ejecuta: make dev-services"
        )
    
    try:
        collections = client_instance.list_collections()
        return [col.name for col in collections]
    except Exception as e:
        raise Exception(f"Error al listar colecciones: {str(e)}")


def get_collection_info(collection_name: str) -> Dict[str, Any]:
    """
    Obtener información sobre una colección (count, metadata, etc.)
    
    Args:
        collection_name: Nombre de la colección
        
    Returns:
        Dict con información de la colección
    """
    client_instance = _get_client()
    if client_instance is None:
        raise Exception(
            f"ChromaDB no está disponible. "
            f"Asegúrate de que ChromaDB esté corriendo en {CHROMA_HOST}:{CHROMA_PORT}. "
            f"En desarrollo local, ejecuta: make dev-services"
        )
    
    try:
        collection = get_collection(collection_name)
        count = collection.count()
        
        return {
            "collection": collection_name,
            "count": count,
            "metadata": collection.metadata or {}
        }
    except Exception as e:
        error_msg = str(e)
        if "ChromaDB no está disponible" in error_msg:
            raise Exception(error_msg)
        raise Exception(f"Error al obtener información de la colección: {error_msg}")


def mmr_search(
    collection_name: str,
    query: str,
    k: int = 4,
    fetch_k: int = 20,
    lambda_mult: float = 0.5,
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Maximum Marginal Relevance (MMR) search usando LangChain con ChromaDB
    
    MMR busca maximizar la relevancia mientras minimiza la redundancia entre documentos.
    Selecciona documentos que son relevantes al query pero diversos entre sí.
    
    Args:
        collection_name: Nombre de la colección
        query: Texto de búsqueda
        k: Número final de documentos a retornar (default: 4)
        fetch_k: Número de documentos candidatos a recuperar inicialmente (default: 20)
        lambda_mult: Factor de diversidad (0.0 = solo relevancia, 1.0 = solo diversidad, default: 0.5)
        filters: Filtros opcionales para aplicar (default: None)
        
    Returns:
        Dict con los resultados de la búsqueda MMR
    """
    client_instance = _get_client()
    if client_instance is None:
        raise Exception(
            f"ChromaDB no está disponible. "
            f"Asegúrate de que ChromaDB esté corriendo en {CHROMA_HOST}:{CHROMA_PORT}. "
            f"En desarrollo local, ejecuta: make dev-services"
        )
    
    if not OPENAI_API_KEY:
        raise Exception("OPENAI_API_KEY no está configurada. Se requiere para embeddings.")
    
    try:
        # Inicializar embeddings de OpenAI
        embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY, model=EMBEDDING_MODEL)
        
        # Crear vector store de LangChain conectado a ChromaDB existente
        vector_store = LangChainChroma(
            client=client_instance,
            collection_name=collection_name,
            embedding_function=embeddings
        )
        
        # Crear retriever MMR
        retriever = vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": k,
                "fetch_k": fetch_k,
                "lambda_mult": lambda_mult
            }
        )
        
        # Limpiar filtros si se proporcionan
        if filters:
            cleaned_filters = {}
            for key, value in filters.items():
                if key.startswith("additionalProp"):
                    continue
                if value is not None and value != "":
                    if isinstance(value, dict):
                        if value:
                            cleaned_filters[key] = value
                    else:
                        cleaned_filters[key] = value
            
            if cleaned_filters:
                # Aplicar filtros usando el retriever
                retriever = vector_store.as_retriever(
                    search_type="mmr",
                    search_kwargs={
                        "k": k,
                        "fetch_k": fetch_k,
                        "lambda_mult": lambda_mult,
                        "filter": cleaned_filters
                    }
                )
        
        # Ejecutar búsqueda MMR
        docs = retriever.invoke(query)
        
        # Procesar resultados
        processed_results = []
        for doc in docs:
            # Extraer metadata y score si están disponibles
            metadata = doc.metadata if hasattr(doc, 'metadata') else {}
            score = metadata.get('score', 0.0) if isinstance(metadata, dict) else 0.0
            
            # Obtener ID del documento
            doc_id = metadata.get('id', '') if isinstance(metadata, dict) else ''
            
            processed_results.append({
                "id": doc_id,
                "document": doc.page_content if hasattr(doc, 'page_content') else str(doc),
                "score": float(score),
                "metadata": metadata if isinstance(metadata, dict) else {}
            })
        
        return {
            "results": processed_results,
            "count": len(processed_results),
            "search_type": "mmr_langchain"
        }
    except Exception as e:
        raise Exception(f"Error en búsqueda MMR: {str(e)}")

