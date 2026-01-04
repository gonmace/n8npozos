"""
Retriever optimizado para RAG (Retrieval Augmented Generation)
Proporciona diferentes estrategias de recuperación de documentos con umbrales de similitud
"""
from typing import List, Dict, Any, Optional, Tuple
from chromadb_client import mmr_search
import statistics


class RAGRetriever:
    """
    Retriever para RAG con múltiples estrategias de búsqueda y umbrales de similitud
    """
    
    def __init__(
        self,
        collection_name: str,
        strategy: str = "hybrid",
        dense_weight: float = 0.7,
        sparse_weight: float = 0.3,
        top_k: int = 5,
        score_threshold: Optional[float] = None,
        similarity_threshold_mode: str = "relative",
        similarity_threshold: float = 0.5,
        min_documents: int = 1
    ):
        """
        Inicializar retriever
        
        Args:
            collection_name: Nombre de la colección en ChromaDB
            strategy: Estrategia de búsqueda ("hybrid", "dense", "sparse", "ensemble")
            dense_weight: Peso para búsqueda densa (solo para hybrid)
            sparse_weight: Peso para búsqueda sparse (solo para hybrid)
            top_k: Número de documentos a recuperar
            score_threshold: Umbral mínimo absoluto de score (opcional)
            similarity_threshold_mode: Modo de umbral ("absolute", "relative", "percentile")
            similarity_threshold: Valor del umbral según el modo:
                - "absolute": Score mínimo absoluto (ej: 0.01)
                - "relative": Porcentaje del score máximo (ej: 0.5 = 50% del máximo)
                - "percentile": Percentil de scores (ej: 0.75 = percentil 75)
            min_documents: Número mínimo de documentos requeridos para considerar válido
        """
        self.collection_name = collection_name
        self.strategy = strategy
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight
        self.top_k = top_k
        self.score_threshold = score_threshold
        self.similarity_threshold_mode = similarity_threshold_mode
        self.similarity_threshold = similarity_threshold
        self.min_documents = min_documents
    
    def retrieve(
        self, 
        query: str, 
        filters: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Recuperar documentos relevantes para una consulta con evaluación de umbral
        
        Args:
            query: Consulta del usuario
            filters: Filtros opcionales para aplicar
            
        Returns:
            Tuple de (documentos filtrados, metadatos de evaluación):
            - documentos: Lista de documentos que pasan el umbral
            - metadatos: Dict con información sobre la evaluación:
                - "total_retrieved": Total de documentos recuperados
                - "filtered_count": Documentos que pasan el umbral
                - "max_score": Score máximo encontrado
                - "min_score": Score mínimo de documentos filtrados
                - "threshold_used": Umbral aplicado
                - "is_valid": Si hay suficientes documentos válidos
                - "threshold_mode": Modo de umbral usado
        """
        # Obtener documentos según estrategia
        if self.strategy == "hybrid":
            documents = self._hybrid_retrieve(query, filters)
        elif self.strategy == "dense":
            documents = self._dense_retrieve(query, filters)
        elif self.strategy == "sparse":
            documents = self._sparse_retrieve(query, filters)
        elif self.strategy == "ensemble":
            documents = self._ensemble_retrieve(query, filters)
        else:
            raise ValueError(f"Estrategia desconocida: {self.strategy}")
        
        # Aplicar umbral de similitud
        filtered_docs, metadata = self._apply_similarity_threshold(documents)
        
        return filtered_docs, metadata
    
    def _apply_similarity_threshold(
        self, 
        documents: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Aplicar umbral de similitud a los documentos recuperados
        
        Args:
            documents: Lista de documentos con scores
            
        Returns:
            Tuple de (documentos filtrados, metadatos)
        """
        if not documents:
            return [], {
                "total_retrieved": 0,
                "filtered_count": 0,
                "max_score": 0.0,
                "min_score": 0.0,
                "threshold_used": 0.0,
                "is_valid": False,
                "threshold_mode": self.similarity_threshold_mode
            }
        
        # Extraer scores
        scores = [doc.get("score", 0.0) for doc in documents]
        max_score = max(scores) if scores else 0.0
        min_score = min(scores) if scores else 0.0
        
        # Calcular umbral según el modo
        if self.similarity_threshold_mode == "absolute":
            threshold = self.similarity_threshold
        elif self.similarity_threshold_mode == "relative":
            threshold = max_score * self.similarity_threshold
        elif self.similarity_threshold_mode == "percentile":
            if len(scores) > 1:
                threshold = statistics.quantiles(scores, n=100)[int(self.similarity_threshold * 100) - 1]
            else:
                threshold = scores[0] if scores else 0.0
        else:
            raise ValueError(f"Modo de umbral desconocido: {self.similarity_threshold_mode}")
        
        # Aplicar umbral absoluto adicional si está configurado
        if self.score_threshold:
            threshold = max(threshold, self.score_threshold)
        
        # Filtrar documentos
        filtered_docs = [doc for doc in documents if doc.get("score", 0.0) >= threshold]
        
        # Evaluar si hay suficientes documentos válidos
        is_valid = len(filtered_docs) >= self.min_documents
        
        metadata = {
            "total_retrieved": len(documents),
            "filtered_count": len(filtered_docs),
            "max_score": max_score,
            "min_score": min(filtered_docs, key=lambda x: x.get("score", 0.0)).get("score", 0.0) if filtered_docs else 0.0,
            "threshold_used": threshold,
            "is_valid": is_valid,
            "threshold_mode": self.similarity_threshold_mode,
            "all_scores": scores[:10]  # Primeros 10 scores para debugging
        }
        
        return filtered_docs, metadata
    
    def _hybrid_retrieve(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Búsqueda MMR con balance medio entre relevancia y diversidad
        """
        results = mmr_search(
            collection_name=self.collection_name,
            query=query,
            k=self.top_k,
            fetch_k=self.top_k * 4,  # Más candidatos para mejor diversidad
            lambda_mult=0.5,  # Balance medio
            filters=filters
        )
        
        documents = results.get("results", [])
        return documents
    
    def _dense_retrieve(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Búsqueda MMR enfocada en relevancia (lambda_mult bajo)
        """
        results = mmr_search(
            collection_name=self.collection_name,
            query=query,
            k=self.top_k,
            fetch_k=self.top_k * 3,
            lambda_mult=0.2,  # Más relevancia, menos diversidad
            filters=filters
        )
        
        documents = results.get("results", [])
        return documents
    
    def _sparse_retrieve(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Búsqueda MMR enfocada en diversidad (lambda_mult alto)
        """
        results = mmr_search(
            collection_name=self.collection_name,
            query=query,
            k=self.top_k,
            fetch_k=self.top_k * 5,  # Muchos candidatos para máxima diversidad
            lambda_mult=0.8,  # Más diversidad
            filters=filters
        )
        
        documents = results.get("results", [])
        return documents
    
    def _ensemble_retrieve(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Ensemble: combina múltiples búsquedas MMR con diferentes parámetros
        """
        # Obtener resultados con diferentes configuraciones de MMR
        results_relevance = mmr_search(
            collection_name=self.collection_name,
            query=query,
            k=self.top_k * 2,
            fetch_k=self.top_k * 4,
            lambda_mult=0.2,  # Alta relevancia
            filters=filters
        )
        
        results_diversity = mmr_search(
            collection_name=self.collection_name,
            query=query,
            k=self.top_k * 2,
            fetch_k=self.top_k * 6,
            lambda_mult=0.8,  # Alta diversidad
            filters=filters
        )
        
        # Combinar y deduplicar por ID
        seen_ids = set()
        combined_docs = []
        
        # Agregar resultados de relevancia primero
        for doc in results_relevance.get("results", []):
            doc_id = doc.get("id")
            if doc_id and doc_id not in seen_ids:
                seen_ids.add(doc_id)
                combined_docs.append(doc)
        
        # Agregar resultados de diversidad después
        for doc in results_diversity.get("results", []):
            doc_id = doc.get("id")
            if doc_id and doc_id not in seen_ids:
                seen_ids.add(doc_id)
                combined_docs.append(doc)
        
        # Limitar a top_k
        combined_docs = combined_docs[:self.top_k]
        
        return combined_docs


def get_best_retriever(
    collection_name: str,
    use_case: str = "general",
    top_k: int = 5,
    similarity_threshold_mode: str = "relative",
    similarity_threshold: float = 0.5,
    min_documents: int = 1
) -> RAGRetriever:
    """
    Factory function para obtener el mejor retriever según el caso de uso
    
    Args:
        collection_name: Nombre de la colección
        use_case: Tipo de caso de uso:
            - "general": Búsqueda general (hybrid recomendado)
            - "semantic": Consultas conceptuales (dense)
            - "exact": Búsqueda de términos exactos (sparse)
            - "comprehensive": Máxima cobertura (ensemble)
        top_k: Número de documentos a recuperar
        similarity_threshold_mode: Modo de umbral ("absolute", "relative", "percentile")
        similarity_threshold: Valor del umbral según el modo
        min_documents: Número mínimo de documentos requeridos
        
    Returns:
        RAGRetriever configurado
    """
    if use_case == "general":
        return RAGRetriever(
            collection_name=collection_name,
            strategy="hybrid",
            dense_weight=0.7,
            sparse_weight=0.3,
            top_k=top_k,
            similarity_threshold_mode=similarity_threshold_mode,
            similarity_threshold=similarity_threshold,
            min_documents=min_documents
        )
    elif use_case == "semantic":
        return RAGRetriever(
            collection_name=collection_name,
            strategy="dense",
            top_k=top_k,
            similarity_threshold_mode=similarity_threshold_mode,
            similarity_threshold=similarity_threshold,
            min_documents=min_documents
        )
    elif use_case == "exact":
        return RAGRetriever(
            collection_name=collection_name,
            strategy="sparse",
            top_k=top_k,
            similarity_threshold_mode=similarity_threshold_mode,
            similarity_threshold=similarity_threshold,
            min_documents=min_documents
        )
    elif use_case == "comprehensive":
        return RAGRetriever(
            collection_name=collection_name,
            strategy="ensemble",
            top_k=top_k,
            similarity_threshold_mode=similarity_threshold_mode,
            similarity_threshold=similarity_threshold,
            min_documents=min_documents
        )
    else:
        # Default: hybrid
        return RAGRetriever(
            collection_name=collection_name,
            strategy="hybrid",
            top_k=top_k,
            similarity_threshold_mode=similarity_threshold_mode,
            similarity_threshold=similarity_threshold,
            min_documents=min_documents
        )

