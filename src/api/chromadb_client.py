"""
Cliente para interactuar con ChromaDB usando LangChain
Proporciona funciones para obtener vectores y documentos de colecciones
"""
import os
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Optional, Any
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from langchain_chroma import Chroma as LangChainChroma
from langchain_openai import OpenAIEmbeddings

# Configuración desde variables de entorno
# Detectar si estamos en Docker o desarrollo local
CHROMA_HOST_ENV = os.getenv("CHROMA_HOST")

# Si CHROMA_HOST está explícitamente configurado, usarlo
if CHROMA_HOST_ENV:
    CHROMA_HOST = CHROMA_HOST_ENV
else:
    # Detectar si estamos en Docker
    is_docker = False
    try:
        # Método 1: Verificar /proc/1/cgroup
        with open("/proc/1/cgroup", "r") as f:
            if "docker" in f.read():
                is_docker = True
    except:
        pass
    
    # Método 2: Verificar si el hostname es el nombre del servicio Docker
    try:
        import socket
        hostname = socket.gethostname()
        if hostname == "api":  # Nombre del contenedor API
            is_docker = True
    except:
        pass
    
    if is_docker:
        CHROMA_HOST = "chroma"  # Nombre del servicio Docker
    else:
        CHROMA_HOST = "localhost"  # Desarrollo local

# Puerto: en desarrollo local con Docker, usar 8008 (puerto mapeado)
# En Docker, usar 8000 (puerto interno)
CHROMA_PORT_ENV = os.getenv("CHROMA_PORT")
if CHROMA_PORT_ENV:
    CHROMA_PORT = int(CHROMA_PORT_ENV)
else:
    # Si estamos en Docker (hostname es "api"), usar puerto interno 8000
    # Si no, usar puerto mapeado 8008
    CHROMA_PORT = 8000 if CHROMA_HOST == "chroma" else 8008
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
    min_score: float = 0.4,
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
        filters: Filtros opcionales para aplicar sobre metadatos (default: None)
                 Si es None o está vacío, se consideran TODOS los documentos sin filtrar.
                 Ejemplo: {"categoria": "precio"} filtrará solo documentos con categoria="precio"
                 Puede usar múltiples filtros: {"categoria": "precio", "tipo": "servicio"}
        min_score: Score mínimo de similitud para incluir un documento (default: 0.4)
        
    Returns:
        Dict con los resultados de la búsqueda MMR filtrados por min_score
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
        
        # Limpiar y preparar filtros de metadatos si se proporcionan
        cleaned_filters = None
        if filters:
            cleaned_filters = {}
            for key, value in filters.items():
                # Ignorar campos adicionales generados automáticamente
                if key.startswith("additionalProp"):
                    continue
                # Solo incluir valores válidos (no None, no vacíos)
                if value is not None and value != "":
                    if isinstance(value, dict):
                        # Si es un dict, solo incluir si no está vacío
                        if value:
                            cleaned_filters[key] = value
                    elif isinstance(value, list):
                        # Si es una lista, incluir si no está vacía
                        if value:
                            cleaned_filters[key] = value
                    else:
                        # Para strings, números, booleans, etc., incluir directamente
                        cleaned_filters[key] = value
            
            # Si después de limpiar no quedan filtros válidos, tratar como None
            if not cleaned_filters:
                cleaned_filters = None
        
        # Preparar parámetros para MMR search
        kwargs_mmr = {
            "k": k,
            "fetch_k": fetch_k,
            "lambda_mult": lambda_mult
        }
        
        # Aplicar filtros de metadatos si existen
        # ChromaDB/LangChain espera filtros en formato: {"metadata_field": "value"}
        # o {"metadata_field": {"$eq": "value"}} para operadores avanzados
        chroma_filters = None
        if cleaned_filters:
            # Convertir filtros simples al formato que ChromaDB espera
            chroma_filters = {}
            for key, value in cleaned_filters.items():
                # Si el valor es un string simple, usar formato directo
                # ChromaDB acepta: {"categoria": "precio"}
                chroma_filters[key] = value
            
            kwargs_mmr["filter"] = chroma_filters
            print(f"🔍 Aplicando filtros de metadatos: {chroma_filters}")
        
        # Obtener documentos MMR seleccionados
        docs = vector_store.max_marginal_relevance_search(query, **kwargs_mmr)
        
        # Verificar que los documentos obtenidos cumplan con los filtros (doble verificación)
        # Esto asegura que incluso si LangChain no aplica los filtros correctamente, los filtramos manualmente
        if chroma_filters and docs:
            original_count = len(docs)
            filtered_docs = []
            for doc in docs:
                doc_metadata = {}
                if hasattr(doc, 'metadata') and doc.metadata:
                    doc_metadata = doc.metadata if isinstance(doc.metadata, dict) else {}
                
                # Verificar que el documento cumpla con todos los filtros
                matches_all_filters = True
                for filter_key, filter_value in chroma_filters.items():
                    doc_value = doc_metadata.get(filter_key)
                    if doc_value != filter_value:
                        matches_all_filters = False
                        break
                
                if matches_all_filters:
                    filtered_docs.append(doc)
            
            docs = filtered_docs
            if len(filtered_docs) < original_count:
                print(f"⚠️  Filtrado post-MMR: {original_count} documentos antes, {len(filtered_docs)} después de aplicar filtros")
        
        # Calcular scores de similitud para evaluar relevancia
        # Obtener embedding del query
        query_embedding = embeddings.embed_query(query)
        query_embedding_np = np.array(query_embedding).reshape(1, -1)
        
        # Extraer IDs de los documentos MMR
        doc_ids_from_mmr = []
        for doc in docs:
            doc_id = ""
            if hasattr(doc, 'metadata') and doc.metadata:
                metadata = doc.metadata if isinstance(doc.metadata, dict) else {}
                doc_id = metadata.get('id') or metadata.get('_id') or metadata.get('doc_id') or ""
            if not doc_id and hasattr(doc, 'id'):
                doc_id = str(doc.id)
            if doc_id:
                doc_ids_from_mmr.append(doc_id)
        
        # Obtener embeddings desde ChromaDB y calcular similitud coseno
        doc_scores_map = {}
        if doc_ids_from_mmr:
            try:
                collection = get_collection(collection_name)
                embeddings_result = collection.get(
                    ids=doc_ids_from_mmr,
                    include=["embeddings"]
                )
                
                if embeddings_result and embeddings_result.get("ids"):
                    for i, doc_id in enumerate(embeddings_result["ids"]):
                        if i < len(embeddings_result.get("embeddings", [])):
                            doc_emb = np.array(embeddings_result["embeddings"][i])
                            doc_emb_np = doc_emb.reshape(1, -1)
                            
                            # Calcular similitud coseno
                            similarity = cosine_similarity(query_embedding_np, doc_emb_np)[0][0]
                            doc_scores_map[doc_id] = float(similarity)
            except Exception as e:
                print(f"⚠️  Error al calcular scores: {e}")
        
        # Procesar resultados
        processed_results = []
        for i, doc in enumerate(docs):
            # Extraer metadata
            metadata = {}
            if hasattr(doc, 'metadata') and doc.metadata:
                metadata = doc.metadata if isinstance(doc.metadata, dict) else {}
            
            # Obtener ID del documento - puede estar en diferentes lugares
            doc_id = ""
            if isinstance(metadata, dict):
                # Intentar diferentes campos comunes para ID
                doc_id = metadata.get('id') or metadata.get('_id') or metadata.get('doc_id') or ""
            
            # Si no hay ID en metadata, intentar obtenerlo del documento directamente
            if not doc_id and hasattr(doc, 'id'):
                doc_id = str(doc.id)
            
            # Obtener el contenido del documento
            document_content = ""
            if hasattr(doc, 'page_content'):
                document_content = doc.page_content
            elif hasattr(doc, 'content'):
                document_content = doc.content
            else:
                document_content = str(doc)
            
            # Obtener score de similitud para evaluar relevancia
            similarity_score = doc_scores_map.get(doc_id, None) if doc_id else None
            
            # Limpiar metadata para remover campos internos de LangChain si es necesario
            clean_metadata = {}
            if isinstance(metadata, dict):
                for key, value in metadata.items():
                    # Excluir campos internos que no queremos exponer
                    if not key.startswith('_') and key not in ['score', 'relevance_score', 'distance']:
                        clean_metadata[key] = value
            
            result = {
                "id": str(doc_id) if doc_id else f"doc_{i}",
                "document": document_content,
                "metadata": clean_metadata
            }
            
            # Agregar score de similitud si está disponible
            if similarity_score is not None:
                result["similarity_score"] = similarity_score
            
            # Filtrar por min_score: solo incluir documentos con score >= min_score
            if similarity_score is not None and similarity_score >= min_score:
                processed_results.append(result)
            elif similarity_score is None:
                # Si no hay score disponible, incluir el documento (por compatibilidad)
                processed_results.append(result)
        
        return {
            "results": processed_results,
            "count": len(processed_results),
            "search_type": "mmr_langchain",
            "min_score": min_score
        }
    except Exception as e:
        raise Exception(f"Error en búsqueda MMR: {str(e)}")

