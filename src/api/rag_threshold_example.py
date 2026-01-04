"""
Ejemplos de uso del sistema de umbrales de similitud en RAG
"""
from rag_retriever import RAGRetriever, get_best_retriever


def example_relative_threshold():
    """
    Ejemplo: Umbral relativo (50% del score máximo)
    Útil cuando quieres documentos que sean al menos la mitad de relevantes que el mejor
    """
    print("=" * 60)
    print("Ejemplo 1: Umbral Relativo (50% del máximo)")
    print("=" * 60)
    
    retriever = RAGRetriever(
        collection_name="pozos",
        strategy="hybrid",
        top_k=10,
        similarity_threshold_mode="relative",
        similarity_threshold=0.5,  # 50% del score máximo
        min_documents=1
    )
    
    documents, metadata = retriever.retrieve("Montero")
    
    print(f"\nTotal recuperados: {metadata['total_retrieved']}")
    print(f"Documentos filtrados: {metadata['filtered_count']}")
    print(f"Score máximo: {metadata['max_score']:.4f}")
    print(f"Score mínimo (filtrado): {metadata['min_score']:.4f}")
    print(f"Umbral usado: {metadata['threshold_used']:.4f}")
    print(f"¿Es válido?: {metadata['is_valid']}")
    
    if metadata['is_valid']:
        print(f"\n✅ Documentos válidos encontrados:")
        for i, doc in enumerate(documents[:3], 1):
            print(f"  {i}. Score: {doc['score']:.4f} - {doc['document'][:60]}...")
    else:
        print("\n❌ No hay documentos suficientemente relevantes")


def example_absolute_threshold():
    """
    Ejemplo: Umbral absoluto (score mínimo fijo)
    Útil cuando conoces el rango de scores y quieres un mínimo fijo
    """
    print("\n" + "=" * 60)
    print("Ejemplo 2: Umbral Absoluto (score mínimo: 0.01)")
    print("=" * 60)
    
    retriever = RAGRetriever(
        collection_name="pozos",
        strategy="hybrid",
        top_k=10,
        similarity_threshold_mode="absolute",
        similarity_threshold=0.01,  # Score mínimo absoluto
        min_documents=2  # Requiere al menos 2 documentos
    )
    
    documents, metadata = retriever.retrieve("Montero")
    
    print(f"\nTotal recuperados: {metadata['total_retrieved']}")
    print(f"Documentos filtrados: {metadata['filtered_count']}")
    print(f"Score máximo: {metadata['max_score']:.4f}")
    print(f"Score mínimo (filtrado): {metadata['min_score']:.4f}")
    print(f"Umbral usado: {metadata['threshold_used']:.4f}")
    print(f"¿Es válido?: {metadata['is_valid']}")


def example_percentile_threshold():
    """
    Ejemplo: Umbral por percentil (percentil 75)
    Útil cuando quieres los mejores documentos independientemente del score absoluto
    """
    print("\n" + "=" * 60)
    print("Ejemplo 3: Umbral por Percentil (percentil 75)")
    print("=" * 60)
    
    retriever = RAGRetriever(
        collection_name="pozos",
        strategy="hybrid",
        top_k=10,
        similarity_threshold_mode="percentile",
        similarity_threshold=0.75,  # Percentil 75
        min_documents=1
    )
    
    documents, metadata = retriever.retrieve("Montero")
    
    print(f"\nTotal recuperados: {metadata['total_retrieved']}")
    print(f"Documentos filtrados: {metadata['filtered_count']}")
    print(f"Score máximo: {metadata['max_score']:.4f}")
    print(f"Score mínimo (filtrado): {metadata['min_score']:.4f}")
    print(f"Umbral usado: {metadata['threshold_used']:.4f}")
    print(f"Scores encontrados: {metadata.get('all_scores', [])}")
    print(f"¿Es válido?: {metadata['is_valid']}")


def example_strict_threshold():
    """
    Ejemplo: Umbral estricto (solo documentos muy relevantes)
    Útil cuando quieres alta precisión, aunque puedas perder recall
    """
    print("\n" + "=" * 60)
    print("Ejemplo 4: Umbral Estricto (80% del máximo)")
    print("=" * 60)
    
    retriever = RAGRetriever(
        collection_name="pozos",
        strategy="hybrid",
        top_k=10,
        similarity_threshold_mode="relative",
        similarity_threshold=0.8,  # 80% del máximo (muy estricto)
        min_documents=1
    )
    
    documents, metadata = retriever.retrieve("Montero")
    
    print(f"\nTotal recuperados: {metadata['total_retrieved']}")
    print(f"Documentos filtrados: {metadata['filtered_count']}")
    print(f"Score máximo: {metadata['max_score']:.4f}")
    print(f"Umbral usado: {metadata['threshold_used']:.4f}")
    print(f"¿Es válido?: {metadata['is_valid']}")
    
    if metadata['is_valid']:
        print("\n✅ Solo documentos muy relevantes:")
        for i, doc in enumerate(documents, 1):
            print(f"  {i}. Score: {doc['score']:.4f}")


def example_evaluation_workflow():
    """
    Ejemplo: Flujo completo de evaluación
    Evalúa si hay documentos válidos antes de generar respuesta
    """
    print("\n" + "=" * 60)
    print("Ejemplo 5: Flujo Completo de Evaluación")
    print("=" * 60)
    
    retriever = get_best_retriever(
        collection_name="pozos",
        use_case="general",
        top_k=5,
        similarity_threshold_mode="relative",
        similarity_threshold=0.5,
        min_documents=1
    )
    
    queries = [
        "Montero",
        "¿Dónde atienden?",
        "xyz123nonexistent"  # Consulta sin resultados relevantes
    ]
    
    for query in queries:
        print(f"\n--- Consulta: '{query}' ---")
        documents, metadata = retriever.retrieve(query)
        
        print(f"Total recuperados: {metadata['total_retrieved']}")
        print(f"Documentos válidos: {metadata['filtered_count']}")
        print(f"Umbral usado: {metadata['threshold_used']:.4f}")
        print(f"¿Vale la pena usar?: {'✅ SÍ' if metadata['is_valid'] else '❌ NO'}")
        
        if metadata['is_valid']:
            print(f"  → Puedes usar estos {len(documents)} documentos para RAG")
        else:
            print(f"  → No hay documentos suficientemente relevantes")
            print(f"  → Score máximo: {metadata['max_score']:.4f} (umbral: {metadata['threshold_used']:.4f})")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("EJEMPLOS DE UMBRALES DE SIMILITUD PARA RAG")
    print("=" * 60)
    
    example_relative_threshold()
    example_absolute_threshold()
    example_percentile_threshold()
    example_strict_threshold()
    example_evaluation_workflow()
    
    print("\n" + "=" * 60)
    print("RECOMENDACIONES:")
    print("=" * 60)
    print("""
1. Umbral Relativo (0.5-0.7): Mejor para casos generales
   - Se adapta al score máximo de cada consulta
   - Filtra documentos poco relevantes automáticamente

2. Umbral Absoluto: Útil cuando conoces el rango de scores
   - Requiere calibración previa
   - Puede ser muy estricto o muy permisivo según el caso

3. Umbral por Percentil: Útil para mantener consistencia
   - Siempre toma los mejores documentos
   - No depende del score absoluto

4. min_documents: Asegura calidad mínima
   - Si no hay suficientes documentos válidos, no usar RAG
   - Evita respuestas basadas en información insuficiente
    """)

