"""
Ejemplo de implementación RAG completo usando el retriever
"""
from typing import List, Dict, Any, Optional
from rag_retriever import RAGRetriever, get_best_retriever


class RAGPipeline:
    """
    Pipeline completo de RAG: Retrieval + Augmented Generation
    """
    
    def __init__(
        self,
        collection_name: str,
        retriever_strategy: str = "hybrid",
        top_k: int = 5,
        llm_client=None  # OpenAI, Anthropic, etc.
    ):
        """
        Inicializar pipeline RAG
        
        Args:
            collection_name: Nombre de la colección en ChromaDB
            retriever_strategy: Estrategia del retriever ("hybrid", "dense", "sparse", "ensemble")
            top_k: Número de documentos a recuperar
            llm_client: Cliente del LLM (OpenAI, Anthropic, etc.)
        """
        self.retriever = RAGRetriever(
            collection_name=collection_name,
            strategy=retriever_strategy,
            top_k=top_k
        )
        self.llm_client = llm_client
    
    def format_context(self, documents: List[Dict[str, Any]]) -> str:
        """
        Formatear documentos recuperados como contexto para el LLM
        
        Args:
            documents: Lista de documentos recuperados
            
        Returns:
            Contexto formateado como string
        """
        context_parts = []
        
        for i, doc in enumerate(documents, 1):
            doc_text = doc.get("document", "")
            metadata = doc.get("metadata", {})
            score = doc.get("score", 0.0)
            
            # Construir entrada del documento
            entry = f"[Documento {i}] (Relevancia: {score:.4f})\n{doc_text}"
            
            # Agregar metadatos si existen
            if metadata:
                meta_str = ", ".join([f"{k}: {v}" for k, v in metadata.items()])
                entry += f"\nMetadatos: {meta_str}"
            
            context_parts.append(entry)
        
        return "\n\n".join(context_parts)
    
    def build_prompt(
        self,
        query: str,
        context: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Construir prompt para el LLM
        
        Args:
            query: Consulta del usuario
            context: Contexto recuperado de los documentos
            system_prompt: Prompt del sistema (opcional)
            
        Returns:
            Prompt completo
        """
        if system_prompt is None:
            system_prompt = """Eres un asistente útil que responde preguntas basándote en el contexto proporcionado.
Responde de manera clara, precisa y basándote únicamente en la información del contexto.
Si la información no está en el contexto, di que no tienes esa información."""
        
        prompt = f"""{system_prompt}

CONTEXTO:
{context}

PREGUNTA: {query}

RESPUESTA:"""
        
        return prompt
    
    def generate(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generar respuesta usando RAG con evaluación de umbral de similitud
        
        Args:
            query: Consulta del usuario
            filters: Filtros opcionales para la búsqueda
            system_prompt: Prompt del sistema (opcional)
            
        Returns:
            Dict con respuesta, documentos recuperados y metadatos de evaluación
        """
        # 1. Retrieval: Obtener documentos relevantes con evaluación de umbral
        documents, retrieval_metadata = self.retriever.retrieve(query, filters)
        
        # Evaluar si hay documentos válidos suficientes
        if not retrieval_metadata.get("is_valid", False):
            return {
                "answer": "No encontré información suficientemente relevante para tu consulta. "
                         f"Los documentos encontrados no alcanzaron el umbral de similitud requerido "
                         f"(umbral usado: {retrieval_metadata.get('threshold_used', 0):.4f}).",
                "documents": [],
                "context": "",
                "metadata": {
                    "retrieved_count": retrieval_metadata.get("total_retrieved", 0),
                    "filtered_count": retrieval_metadata.get("filtered_count", 0),
                    "strategy": self.retriever.strategy,
                    "is_valid": False,
                    "threshold_used": retrieval_metadata.get("threshold_used", 0),
                    "max_score": retrieval_metadata.get("max_score", 0),
                    "min_score": retrieval_metadata.get("min_score", 0)
                }
            }
        
        # 2. Format context: Formatear documentos como contexto
        context = self.format_context(documents)
        
        # 3. Build prompt: Construir prompt para el LLM
        prompt = self.build_prompt(query, context, system_prompt)
        
        # 4. Generate: Generar respuesta con el LLM
        answer = ""
        if self.llm_client:
            # Aquí integrarías con OpenAI, Anthropic, etc.
            # Ejemplo con OpenAI:
            # response = self.llm_client.chat.completions.create(
            #     model="gpt-4",
            #     messages=[{"role": "user", "content": prompt}]
            # )
            # answer = response.choices[0].message.content
            answer = "[Respuesta del LLM - integrar con OpenAI/Anthropic/etc.]"
        else:
            # Sin LLM, devolver contexto
            answer = f"Contexto recuperado ({len(documents)} documentos):\n\n{context}"
        
        return {
            "answer": answer,
            "documents": documents,
            "context": context,
            "metadata": {
                "retrieved_count": retrieval_metadata.get("total_retrieved", len(documents)),
                "filtered_count": len(documents),
                "strategy": self.retriever.strategy,
                "query": query,
                "is_valid": True,
                "threshold_used": retrieval_metadata.get("threshold_used", 0),
                "max_score": retrieval_metadata.get("max_score", 0),
                "min_score": retrieval_metadata.get("min_score", 0),
                "threshold_mode": retrieval_metadata.get("threshold_mode", "")
            }
        }


# Ejemplo de uso
if __name__ == "__main__":
    # Crear pipeline RAG con retriever híbrido (recomendado)
    rag = RAGPipeline(
        collection_name="pozos",
        retriever_strategy="hybrid",
        top_k=5
    )
    
    # Generar respuesta
    result = rag.generate("¿Atienden en Montero?")
    
    print("Respuesta:", result["answer"])
    print("\nDocumentos recuperados:", len(result["documents"]))
    print("\nEstrategia:", result["metadata"]["strategy"])

