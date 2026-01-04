# Mejores Prácticas para RAG (Retrieval Augmented Generation)

## 🎯 Estrategias de Retriever - Comparación

### 1. **Hybrid Retriever** ⭐ RECOMENDADO

**Cuándo usar:**
- Casos de uso generales
- Contenido técnico o especializado
- Necesitas balance entre significado y términos exactos

**Ventajas:**
- ✅ Mejor precisión que dense o sparse solo
- ✅ Combina semántica (70%) + keywords (30%)
- ✅ Funciona bien con consultas ambiguas
- ✅ Ya implementado en tu código

**Configuración recomendada:**
```python
retriever = RAGRetriever(
    collection_name="pozos",
    strategy="hybrid",
    dense_weight=0.7,  # 70% semántica
    sparse_weight=0.3,  # 30% keywords
    top_k=5
)
```

---

### 2. **Dense Retriever** (Solo Semántico)

**Cuándo usar:**
- Consultas conceptuales o abstractas
- Necesitas entender significado, no términos exactos
- Contenido en diferentes idiomas o sinónimos

**Ventajas:**
- ✅ Entiende significado y sinónimos
- ✅ Funciona con consultas reformuladas
- ✅ Bueno para preguntas abiertas

**Desventajas:**
- ❌ Puede perder términos exactos importantes
- ❌ Menos preciso para nombres propios o términos técnicos

**Ejemplo:**
```python
# Consulta: "¿Dónde prestan servicios?"
# Encuentra documentos sobre "ubicación", "cobertura", "áreas de servicio"
```

---

### 3. **Sparse Retriever** (Solo Keywords)

**Cuándo usar:**
- Búsqueda de términos exactos
- Nombres propios, códigos, IDs
- Consultas muy específicas

**Ventajas:**
- ✅ Excelente para coincidencias exactas
- ✅ Encuentra nombres propios fácilmente
- ✅ Rápido y eficiente

**Desventajas:**
- ❌ No entiende sinónimos
- ❌ Falla con consultas reformuladas
- ❌ No captura significado

**Ejemplo:**
```python
# Consulta: "Montero"
# Solo encuentra documentos que contengan exactamente "Montero"
```

---

### 4. **Ensemble Retriever**

**Cuándo usar:**
- Necesitas máxima cobertura
- No te importa la velocidad
- Quieres todos los documentos relevantes posibles

**Ventajas:**
- ✅ Máxima cobertura
- ✅ No pierde documentos relevantes
- ✅ Combina lo mejor de ambos mundos

**Desventajas:**
- ❌ Más lento (hace 2 búsquedas)
- ❌ Puede traer documentos menos relevantes
- ❌ Requiere más procesamiento

---

## 📊 Comparación de Estrategias

| Estrategia | Precisión | Velocidad | Cobertura | Casos de Uso |
|------------|-----------|-----------|----------|--------------|
| **Hybrid** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | General, técnico |
| **Dense** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Conceptual, abstracto |
| **Sparse** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | Exacto, nombres propios |
| **Ensemble** | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | Máxima cobertura |

---

## 🚀 Recomendaciones por Caso de Uso

### Para tu caso (información sobre servicios):

```python
# RECOMENDADO: Hybrid Retriever
retriever = get_best_retriever(
    collection_name="pozos",
    use_case="general",  # o "semantic" si prefieres más significado
    top_k=5
)
```

**¿Por qué Hybrid?**
- Tus consultas pueden ser: "Montero" (exacto) o "¿Dónde atienden?" (semántico)
- Contenido técnico (servicios, ubicaciones)
- Necesitas balance entre términos exactos y significado

---

## ⚙️ Parámetros Importantes

### `top_k` (Número de documentos)
- **3-5**: Para respuestas concisas, menos contexto
- **5-10**: Balanceado (recomendado)
- **10-20**: Para análisis profundos, más contexto

### `dense_weight` vs `sparse_weight`
- **0.7 / 0.3**: General (recomendado)
- **0.8 / 0.2**: Más semántico, menos keywords
- **0.5 / 0.5**: Balance igual
- **0.3 / 0.7**: Más keywords, menos semántico

### `score_threshold`
- **None**: Sin filtro (recomendado para empezar)
- **0.01**: Filtrar documentos muy poco relevantes
- **0.05**: Solo documentos muy relevantes

---

## 🔧 Optimización del Retriever

### 1. **Ajustar pesos según resultados**
```python
# Si encuentras que faltan términos exactos:
retriever = RAGRetriever(
    strategy="hybrid",
    dense_weight=0.6,  # Reducir
    sparse_weight=0.4  # Aumentar
)

# Si encuentras que faltan sinónimos:
retriever = RAGRetriever(
    strategy="hybrid",
    dense_weight=0.8,  # Aumentar
    sparse_weight=0.2  # Reducir
)
```

### 2. **Usar filtros para contexto específico**
```python
# Filtrar por categoría, fuente, etc.
documents = retriever.retrieve(
    query="Montero",
    filters={"categoria": "servicios", "source": "web"}
)
```

### 3. **Ajustar top_k según necesidad**
```python
# Para respuestas rápidas:
top_k = 3

# Para análisis completos:
top_k = 10
```

---

## 📝 Pipeline RAG Completo

### Estructura recomendada:

```
1. Retrieval (Retriever)
   ↓
2. Format Context (Formatear documentos)
   ↓
3. Build Prompt (Construir prompt con contexto)
   ↓
4. Generate (LLM genera respuesta)
   ↓
5. Post-process (Opcional: citas, validación)
```

### Ejemplo completo:

```python
from src.api.rag_retriever import get_best_retriever
from src.api.rag_example import RAGPipeline

# Crear pipeline
rag = RAGPipeline(
    collection_name="pozos",
    retriever_strategy="hybrid",  # RECOMENDADO
    top_k=5
)

# Generar respuesta
result = rag.generate("¿Atienden en Montero?")

print(result["answer"])
print(f"Documentos: {len(result['documents'])}")
```

---

## 🎓 Mejores Prácticas Generales

1. **Empieza con Hybrid**: Es el mejor balance para la mayoría de casos
2. **Ajusta según resultados**: Prueba diferentes pesos y estrategias
3. **Usa top_k adecuado**: 5-10 es un buen punto de partida
4. **Filtra cuando sea posible**: Usa metadatos para contexto específico
5. **Monitorea scores**: Documentos con score muy bajo pueden ser ruido
6. **Prueba diferentes consultas**: Evalúa con casos reales

---

## 🔍 Cuándo Cambiar de Estrategia

### Cambiar a Dense si:
- Los usuarios hacen preguntas conceptuales
- Necesitas entender sinónimos
- El contenido es abstracto

### Cambiar a Sparse si:
- Los usuarios buscan términos exactos
- Hay muchos nombres propios
- Necesitas coincidencias precisas

### Cambiar a Ensemble si:
- Necesitas máxima cobertura
- No te importa la velocidad
- Quieres todos los documentos posibles

---

## 📈 Métricas para Evaluar

1. **Precisión**: ¿Los documentos recuperados son relevantes?
2. **Recall**: ¿Se recuperan todos los documentos relevantes?
3. **Velocidad**: ¿Qué tan rápido es el retriever?
4. **Cobertura**: ¿Cubre diferentes tipos de consultas?

---

## 💡 Conclusión

**Para tu caso de uso (información sobre servicios):**

✅ **Usa Hybrid Retriever** con:
- `dense_weight=0.7`
- `sparse_weight=0.3`
- `top_k=5`

Esto te dará el mejor balance entre:
- Encontrar términos exactos ("Montero")
- Entender significado ("¿Dónde atienden?")
- Velocidad y precisión

