import os
import uuid
import gradio as gr
import chromadb
from chromadb.utils import embedding_functions

# Configuración desde variables de entorno
# Detectar si estamos en Docker o desarrollo local
# Si CHROMA_HOST no está configurado, detectar automáticamente
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
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "pozos")
GRADIO_AUTH_USERNAME = os.getenv("GRADIO_AUTH_USERNAME", "admin")
GRADIO_AUTH_PASSWORD = os.getenv("GRADIO_AUTH_PASSWORD", "admin123")
GRADIO_SERVER_PORT = int(os.getenv("GRADIO_SERVER_PORT", "7860"))
ENV = os.getenv("ENV", "production")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Configuración del modelo de embedding de OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")

# Inicializar función de embedding de OpenAI
if not OPENAI_API_KEY:
    print("⚠️  ADVERTENCIA: OPENAI_API_KEY no está configurada.")
    print("   Los embeddings usarán el modelo por defecto de ChromaDB.")
    print("   Para usar text-embedding-3-large, configura OPENAI_API_KEY en .env")
    embedding_function = None
else:
    embedding_function = embedding_functions.OpenAIEmbeddingFunction(
        api_key=OPENAI_API_KEY,
        model_name=EMBEDDING_MODEL
    )
    print(f"✅ Usando modelo de embedding: {EMBEDDING_MODEL}")

# Inicializar cliente de ChromaDB con manejo de errores
try:
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    
    # Intentar crear o obtener la colección con el modelo de embedding especificado
    # Si la colección existe con un modelo diferente, eliminarla y crear una nueva
    try:
        if embedding_function:
            collection = client.get_or_create_collection(
                name=COLLECTION_NAME,
                embedding_function=embedding_function
            )
        else:
            collection = client.get_or_create_collection(COLLECTION_NAME)
    except ValueError as ve:
        # Si hay conflicto de embedding function, eliminar la colección existente y crear una nueva
        if "embedding function conflict" in str(ve).lower() or "embedding function already exists" in str(ve).lower():
            print(f"\n⚠️  La colección '{COLLECTION_NAME}' existe con un modelo de embedding diferente.")
            print(f"   Eliminando la colección existente para usar el nuevo modelo...")
            try:
                client.delete_collection(name=COLLECTION_NAME)
                print(f"   ✅ Colección eliminada. Creando nueva colección con modelo: {EMBEDDING_MODEL}")
            except Exception as delete_error:
                print(f"   ⚠️  No se pudo eliminar la colección: {delete_error}")
                print(f"   Intenta eliminarla manualmente o usa un nombre de colección diferente.")
                raise
            
            # Crear la nueva colección con el modelo correcto
            if embedding_function:
                collection = client.get_or_create_collection(
                    name=COLLECTION_NAME,
                    embedding_function=embedding_function
                )
            else:
                collection = client.get_or_create_collection(COLLECTION_NAME)
            print(f"   ✅ Nueva colección creada exitosamente")
        else:
            raise
except Exception as e:
    print(f"\n❌ Error al conectar con ChromaDB en {CHROMA_HOST}:{CHROMA_PORT}")
    print(f"   Error: {str(e)}")
    print(f"\n💡 Asegúrate de que ChromaDB esté corriendo:")
    print(f"   - En Docker: docker-compose --env-file .env -f deploy/docker-compose.yml up -d chroma")
    print(f"   - O ejecuta: make dev-services")
    print(f"   - Verifica el puerto: curl http://localhost:8000/api/v1/heartbeat o curl http://localhost:8008/api/v1/heartbeat")
    raise

def get_or_create_collection():
    """Obtener o crear la colección, manejando reconexiones"""
    global collection
    try:
        # Verificar si la colección existe
        try:
            collection = client.get_collection(name=COLLECTION_NAME)
        except Exception:
            # Si no existe, crearla
            if embedding_function:
                collection = client.create_collection(
                    name=COLLECTION_NAME,
                    embedding_function=embedding_function
                )
            else:
                collection = client.create_collection(name=COLLECTION_NAME)
            print(f"✅ Colección '{COLLECTION_NAME}' creada")
        return collection
    except Exception as e:
        raise Exception(f"Error al obtener/crear colección: {str(e)}")

def crear_embedding(texto, categoria, source):
    """Crear un nuevo embedding en ChromaDB"""
    try:
        if not texto or not texto.strip():
            return "❌ Error: El texto no puede estar vacío", None
        
        # Asegurar que la colección existe
        collection = get_or_create_collection()
        
        # Generar ID único
        doc_id = str(uuid.uuid4())
        
        # Preparar metadatos (solo si hay valores)
        metadata = {}
        if categoria and categoria.strip():
            metadata["categoria"] = categoria.strip()
        if source and source.strip():
            metadata["source"] = source.strip()
        
        # Agregar a la colección
        # ChromaDB no acepta metadatos vacíos, así que solo los pasamos si hay datos
        if metadata:
            collection.add(
                documents=[texto.strip()],
                metadatas=[metadata],
                ids=[doc_id]
            )
        else:
            collection.add(
                documents=[texto.strip()],
                ids=[doc_id]
            )
        
        return f"✅ Embedding creado exitosamente\nID: {doc_id}", ""
    except Exception as e:
        error_msg = f"❌ Error al crear embedding: {str(e)}"
        if DEBUG:
            import traceback
            error_msg += f"\n\n{traceback.format_exc()}"
        return error_msg, texto if texto else ""

def listar():
    """Listar todos los embeddings"""
    try:
        collection = get_or_create_collection()
        data = collection.get(include=["documents", "metadatas"])
        rows = []
        if data.get("ids"):
            for i, doc in enumerate(data["documents"]):
                meta = data["metadatas"][i] if i < len(data["metadatas"]) else {}
                rows.append([
                    data["ids"][i],
                    doc,
                    meta.get("categoria", "") if meta else "",
                    meta.get("source", "") if meta else ""
                ])
        return rows
    except Exception as e:
        error_msg = f"❌ Error al listar: {str(e)}"
        if DEBUG:
            import traceback
            error_msg += f"\n\n{traceback.format_exc()}"
        return [[error_msg, "", "", ""]]

def actualizar_embedding(id_doc, texto, categoria, source):
    """Actualizar un embedding existente"""
    try:
        if not id_doc or not id_doc.strip():
            return "❌ Error: El ID es requerido"
        
        if not texto or not texto.strip():
            return "❌ Error: El texto no puede estar vacío"
        
        # Asegurar que la colección existe
        collection = get_or_create_collection()
        
        # Preparar metadatos (solo si hay valores)
        metadata = {}
        if categoria and categoria.strip():
            metadata["categoria"] = categoria.strip()
        if source and source.strip():
            metadata["source"] = source.strip()
        
        # Actualizar usando upsert (actualiza si existe, crea si no)
        # ChromaDB requiere metadatos, así que siempre pasamos al menos un dict vacío válido
        # Pero primero eliminamos el documento y lo recreamos si no hay metadatos
        if metadata:
            collection.update(
                ids=[id_doc.strip()],
                documents=[texto.strip()],
                metadatas=[metadata]
            )
        else:
            # Si no hay metadatos, eliminamos y recreamos sin metadatos
            collection.delete(ids=[id_doc.strip()])
            collection.add(
                documents=[texto.strip()],
                ids=[id_doc.strip()]
            )
        
        return f"✅ Embedding actualizado exitosamente\nID: {id_doc}"
    except Exception as e:
        error_msg = f"❌ Error al actualizar: {str(e)}"
        if DEBUG:
            import traceback
            error_msg += f"\n\n{traceback.format_exc()}"
        return error_msg

def eliminar_embedding(id_doc):
    """Eliminar un embedding"""
    try:
        if not id_doc or not id_doc.strip():
            return "❌ Error: El ID es requerido"
        
        collection = get_or_create_collection()
        collection.delete(ids=[id_doc.strip()])
        return f"✅ Embedding eliminado exitosamente\nID: {id_doc}"
    except Exception as e:
        error_msg = f"❌ Error al eliminar: {str(e)}"
        if DEBUG:
            import traceback
            error_msg += f"\n\n{traceback.format_exc()}"
        return error_msg

def obtener_embedding(id_doc):
    """Obtener un embedding específico para editar"""
    try:
        if not id_doc or not id_doc.strip():
            return "", "", "", "⚠️ Ingresa un ID para buscar"
        
        collection = get_or_create_collection()
        result = collection.get(
            ids=[id_doc.strip()],
            include=["documents", "metadatas"]
        )
        
        if not result.get("ids") or len(result["ids"]) == 0:
            return "", "", "", f"⚠️ No se encontró un embedding con ID: {id_doc}"
        
        doc = result["documents"][0] if result["documents"] else ""
        
        # Manejar metadatos de forma segura
        if result.get("metadatas") and len(result["metadatas"]) > 0:
            meta = result["metadatas"][0]
            # Asegurarse de que meta es un diccionario
            if meta is None:
                meta = {}
        else:
            meta = {}
        
        return (
            id_doc.strip(),
            doc,
            meta.get("categoria", "") if isinstance(meta, dict) else "",
            meta.get("source", "") if isinstance(meta, dict) else ""
        )
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        if DEBUG:
            import traceback
            error_msg += f"\n\n{traceback.format_exc()}"
        return "", "", "", error_msg

with gr.Blocks(title="Panel Admin - ChromaDB") as demo:
    gr.Markdown("# 🗄️ Panel Admin – ChromaDB")
    gr.Markdown("Gestiona embeddings y documentos en ChromaDB")
    
    with gr.Tabs() as tabs:
        # Pestaña 1: Crear Embeddings
        with gr.Tab("➕ Crear Embedding"):
            gr.Markdown("### Crear un nuevo embedding")
            
            with gr.Row():
                with gr.Column(scale=2):
                    texto_input = gr.Textbox(
                        label="Texto del documento",
                        placeholder="Ingresa el texto que quieres convertir en embedding...",
                        lines=5,
                        max_lines=10
                    )
                
                with gr.Column(scale=1):
                    categoria_input = gr.Textbox(
                        label="Categoría",
                        placeholder="Ej: documentos, preguntas, respuestas",
                        lines=1
                    )
                    source_input = gr.Textbox(
                        label="Fuente",
                        placeholder="Ej: manual, importado, API",
                        lines=1
                    )
            
            crear_btn = gr.Button("✨ Crear Embedding", variant="primary")
            resultado_crear = gr.Textbox(
                label="Resultado",
                interactive=False,
                lines=3
            )
            
            crear_btn.click(
                fn=crear_embedding,
                inputs=[texto_input, categoria_input, source_input],
                outputs=[resultado_crear, texto_input]
            ).then(
                fn=lambda: ("", ""),
                outputs=[categoria_input, source_input]
            )
        
        # Pestaña 2: Listar y Editar
        with gr.Tab("📋 Listar y Editar"):
            gr.Markdown("### Listar todos los embeddings")
            
            with gr.Row():
                listar_btn = gr.Button("🔄 Actualizar Lista", variant="secondary")
            
            tabla = gr.Dataframe(
                headers=["ID", "Texto", "Categoria", "Source"],
                interactive=True,  # Permitir selección y copia de texto
                wrap=True,
                column_widths=["15%", "50%", "20%", "15%"],  # Texto es la columna más grande
                label="Lista de Embeddings (puedes seleccionar y copiar el ID directamente de la tabla)"
            )
            
            # Variable para mantener los datos de la tabla
            tabla_data = gr.State(value=None)
            
            def listar_con_datos():
                """Listar y guardar los datos para poder acceder al ID seleccionado"""
                data = listar()
                return data, data
            
            listar_btn.click(listar_con_datos, outputs=[tabla, tabla_data])
            
            gr.Markdown("---")
            gr.Markdown("### Editar Embedding")
            
            with gr.Row():
                with gr.Column(scale=3):
                    buscar_id = gr.Textbox(
                        label="ID del Embedding a editar",
                        placeholder="Haz clic en una fila de la tabla arriba para copiar automáticamente, o pégalo manualmente",
                        lines=1
                    )
                with gr.Column(scale=1):
                    buscar_btn = gr.Button("🔍 Buscar", variant="secondary")
            
            # Cuando se selecciona una fila en la tabla, copiar el ID directamente al campo de búsqueda
            def on_tabla_select(evt: gr.SelectData, data):
                """Cuando se selecciona una fila, extraer el ID y copiarlo al campo de búsqueda"""
                if evt is not None and data is not None and len(data) > 0:
                    try:
                        # evt.index es una tupla (fila, columna)
                        row_idx = evt.index[0] if isinstance(evt.index, (list, tuple)) else evt.index
                        if row_idx is not None and row_idx < len(data):
                            return data[row_idx][0]  # Retornar el ID (primera columna)
                    except (IndexError, AttributeError, TypeError) as e:
                        if DEBUG:
                            print(f"Error al seleccionar fila: {e}")
                return ""
            
            tabla.select(on_tabla_select, inputs=[tabla_data], outputs=[buscar_id])
            
            with gr.Row():
                with gr.Column(scale=2):
                    edit_texto = gr.Textbox(
                        label="Texto",
                        lines=5,
                        max_lines=10
                    )
                
                with gr.Column(scale=1):
                    edit_categoria = gr.Textbox(
                        label="Categoría",
                        lines=1
                    )
                    edit_source = gr.Textbox(
                        label="Fuente",
                        lines=1
                    )
            
            with gr.Row():
                actualizar_btn = gr.Button("💾 Actualizar", variant="primary")
                eliminar_btn = gr.Button("🗑️ Eliminar", variant="stop")
            
            resultado_editar = gr.Textbox(
                label="Resultado",
                interactive=False,
                lines=3
            )
            
            buscar_btn.click(
                fn=obtener_embedding,
                inputs=[buscar_id],
                outputs=[buscar_id, edit_texto, edit_categoria, edit_source]
            )
            
            actualizar_btn.click(
                fn=actualizar_embedding,
                inputs=[buscar_id, edit_texto, edit_categoria, edit_source],
                outputs=[resultado_editar]
            ).then(
                fn=listar,
                outputs=[tabla]
            )
            
            eliminar_btn.click(
                fn=eliminar_embedding,
                inputs=[buscar_id],
                outputs=[resultado_editar]
            ).then(
                fn=lambda: ("", "", "", ""),
                outputs=[buscar_id, edit_texto, edit_categoria, edit_source]
            ).then(
                fn=listar,
                outputs=[tabla]
            )

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=GRADIO_SERVER_PORT,
        auth=(GRADIO_AUTH_USERNAME, GRADIO_AUTH_PASSWORD),
        share=False,
        show_error=DEBUG
    )
