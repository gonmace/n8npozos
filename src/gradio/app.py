import os
import uuid
import time
import gradio as gr
import chromadb
from chromadb.utils import embedding_functions
import requests
import json

# Configuración desde variables de entorno
# En Docker, siempre usar el nombre del servicio y puerto interno
# En desarrollo local, usar localhost y puerto mapeado

# Primero verificar si las variables están explícitamente configuradas
CHROMA_HOST_ENV = os.getenv("CHROMA_HOST")
CHROMA_PORT_ENV = os.getenv("CHROMA_PORT")

if CHROMA_HOST_ENV:
    # Si CHROMA_HOST está configurado, usarlo directamente
    CHROMA_HOST = CHROMA_HOST_ENV
    CHROMA_PORT = int(CHROMA_PORT_ENV) if CHROMA_PORT_ENV else (8000 if CHROMA_HOST == "chroma" else 8008)
else:
    # Si no está configurado, detectar automáticamente si estamos en Docker
    try:
        with open("/proc/1/cgroup", "r") as f:
            if "docker" in f.read():
                CHROMA_HOST = "chroma"  # Nombre del servicio Docker
                CHROMA_PORT = int(CHROMA_PORT_ENV) if CHROMA_PORT_ENV else 8000  # Puerto interno de Docker
            else:
                CHROMA_HOST = "localhost"  # Desarrollo local
                CHROMA_PORT = int(CHROMA_PORT_ENV) if CHROMA_PORT_ENV else 8008  # Puerto mapeado
    except:
        # Por defecto, asumir desarrollo local
        CHROMA_HOST = "localhost"
        CHROMA_PORT = int(CHROMA_PORT_ENV) if CHROMA_PORT_ENV else 8008

# Debug: mostrar configuración final y variables de entorno
print(f"🔧 Configuración ChromaDB:")
print(f"   CHROMA_HOST (env): {os.getenv('CHROMA_HOST', 'NO CONFIGURADO')}")
print(f"   CHROMA_PORT (env): {os.getenv('CHROMA_PORT', 'NO CONFIGURADO')}")
print(f"   CHROMA_HOST (final): {CHROMA_HOST}")
print(f"   CHROMA_PORT (final): {CHROMA_PORT}")
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "pozos")
GRADIO_AUTH_USERNAME = os.getenv("GRADIO_AUTH_USERNAME", "admin")
GRADIO_AUTH_PASSWORD = os.getenv("GRADIO_AUTH_PASSWORD", "admin123")
GRADIO_SERVER_PORT = int(os.getenv("GRADIO_SERVER_PORT", "7860"))
GRADIO_ROOT_PATH = os.getenv("GRADIO_ROOT_PATH", "")
ENV = os.getenv("ENV", "production")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Configuración de n8n
N8N_HOST = os.getenv("N8N_HOST", "localhost")
N8N_PORT = os.getenv("N8N_PORT", "5678")
N8N_PROTOCOL = os.getenv("N8N_PROTOCOL", "http")
N8N_WEBHOOK_PATH = os.getenv("N8N_WEBHOOK_PATH", "data_test")
# Construir URL de n8n: en Docker usar el nombre del servicio, en local usar localhost
try:
    with open("/proc/1/cgroup", "r") as f:
        if "docker" in f.read():
            N8N_URL = f"http://n8n:5678/webhook/{N8N_WEBHOOK_PATH}"  # Puerto interno de Docker
        else:
            N8N_URL = f"{N8N_PROTOCOL}://{N8N_HOST}:{N8N_PORT}/webhook/{N8N_WEBHOOK_PATH}"
except:
    N8N_URL = f"{N8N_PROTOCOL}://{N8N_HOST}:{N8N_PORT}/webhook/{N8N_WEBHOOK_PATH}"

print(f"🔧 Configuración n8n:")
print(f"   N8N_URL: {N8N_URL}")

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

# Inicializar cliente de ChromaDB con manejo de errores y reintentos
max_retries = 15  # Aumentar intentos para dar más tiempo a ChromaDB
retry_delay = 4  # Aumentar tiempo de espera entre intentos (ChromaDB puede tardar en iniciar)

# Función auxiliar para verificar si ChromaDB está listo antes de crear el cliente
def _check_chromadb_ready(host: str, port: int) -> bool:
    """Verifica si ChromaDB está listo para recibir conexiones"""
    try:
        import urllib.request
        import urllib.error
        # Intentar con v1 primero (puede estar deprecado pero aún responde)
        url = f"http://{host}:{port}/api/v1/heartbeat"
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'ChromaDB-Health-Check')
        try:
            with urllib.request.urlopen(req, timeout=2) as response:
                # Cualquier respuesta HTTP válida indica que ChromaDB está corriendo
                return True
        except urllib.error.HTTPError:
            # HTTPError (4xx, 5xx) significa que el servidor respondió
            # Esto indica que ChromaDB está corriendo y respondiendo
            return True
    except (urllib.error.URLError, OSError, ConnectionError, TimeoutError) as e:
        # Solo retornar False si es un error de conexión real
        error_str = str(e).lower()
        if any(keyword in error_str for keyword in ["connection refused", "connection reset", "timeout", "errno 104", "errno 111"]):
            return False
        # Para otros errores desconocidos, asumir que no está listo
        return False
    except Exception:
        # Cualquier otra excepción, asumir que no está listo
        return False

client = None
for attempt in range(max_retries):
    try:
        # Primero verificar si ChromaDB está listo antes de intentar crear el cliente
        if not _check_chromadb_ready(CHROMA_HOST, CHROMA_PORT):
            if attempt < max_retries - 1:
                print(f"⚠️  Intento {attempt + 1}/{max_retries}: ChromaDB aún no responde en {CHROMA_HOST}:{CHROMA_PORT}, esperando {retry_delay}s...")
                time.sleep(retry_delay)
                continue
        
        # Intentar crear el cliente
        # Nota: ChromaDB puede intentar autenticarse durante la inicialización
        # Si ChromaDB no tiene auth configurada, esto puede fallar temporalmente
        # Usar Settings para evitar problemas de autenticación
        try:
            from chromadb.config import Settings
            client = chromadb.HttpClient(
                host=CHROMA_HOST,
                port=CHROMA_PORT,
                settings=Settings(anonymized_telemetry=False)
            )
        except (ImportError, TypeError, ValueError) as settings_error:
            # Si Settings no está disponible o falla, usar método simple
            # Si falla con ValueError (error de auth), capturarlo y reintentar
            error_msg = str(settings_error)
            if "Connection reset" in error_msg or "auth" in error_msg.lower():
                # Si es un error de conexión o auth, reintentar
                raise settings_error
            client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        
        # Verificar que ChromaDB esté respondiendo intentando listar colecciones
        # Esto también verifica que la conexión esté completamente establecida
        # Esperar un poco antes de verificar para dar tiempo a ChromaDB
        time.sleep(1)
        try:
            client.list_collections()
        except Exception as verify_error:
            # Si list_collections falla, puede ser que ChromaDB aún esté iniciando
            # Intentar heartbeat como verificación alternativa
            try:
                client.heartbeat()
            except Exception:
                # Si ambos fallan, aún así mantener el cliente (puede funcionar para operaciones básicas)
                # pero solo si no es un error de conexión
                verify_error_msg = str(verify_error)
                if "Connection reset" in verify_error_msg or "Connection refused" in verify_error_msg:
                    raise verify_error  # Re-lanzar para que se maneje en el bloque externo
        
        if attempt > 0:
            print(f"✅ Conectado a ChromaDB después de {attempt + 1} intentos")
        break
    except (ValueError, Exception) as e:
        error_msg = str(e)
        # Si es un error de conexión o autenticación, esperar y reintentar
        if "Connection reset" in error_msg or "Connection refused" in error_msg or "Connection reset by peer" in error_msg or "auth/identity" in error_msg.lower():
            if attempt < max_retries - 1:
                print(f"⚠️  Intento {attempt + 1}/{max_retries} de conexión a ChromaDB falló (ChromaDB aún iniciando), reintentando en {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                print(f"\n❌ Error al conectar con ChromaDB en {CHROMA_HOST}:{CHROMA_PORT}")
                print(f"   Error: {error_msg}")
                print(f"\n💡 ChromaDB parece estar iniciando o no está respondiendo correctamente.")
                print(f"   Verifica el estado:")
                print(f"   - docker ps | grep chroma")
                print(f"   - docker logs chroma --tail 20")
                print(f"   - curl http://localhost:{CHROMA_PORT}/api/v1/heartbeat")
                print(f"\n   Si ChromaDB está corriendo, espera unos segundos más y vuelve a intentar.")
                raise
        else:
            # Para otros errores, también reintentar pero mostrar el error específico
            if attempt < max_retries - 1:
                print(f"⚠️  Intento {attempt + 1}/{max_retries} falló: {error_msg[:100]}...")
                print(f"   Reintentando en {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                print(f"\n❌ Error al conectar con ChromaDB después de {max_retries} intentos")
                print(f"   Error: {error_msg}")
                raise

try:
    
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
    print(f"   - Verifica el puerto: curl http://localhost:8008/api/v2/heartbeat")
    print(f"   - Si ChromaDB está en Docker, espera unos segundos para que inicie completamente")
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

def procesar_archivo_whatsapp(archivo, n8n_url):
    """Procesar archivo txt o JSON de WhatsApp y enviarlo a n8n"""
    try:
        if archivo is None:
            return "❌ Error: No se ha seleccionado ningún archivo"
        
        if not n8n_url or not n8n_url.strip():
            return "❌ Error: Debes ingresar la URL de n8n"
        
        # Validar que la URL sea válida
        url_limpia = n8n_url.strip()
        if not url_limpia.startswith(('http://', 'https://')):
            return "❌ Error: La URL debe comenzar con http:// o https://"
        
        # Obtener la ruta del archivo (Gradio con type="filepath" devuelve una cadena)
        file_path = archivo if isinstance(archivo, str) else (archivo.name if hasattr(archivo, 'name') else str(archivo))
        
        if not file_path or not os.path.exists(file_path):
            return "❌ Error: El archivo no existe o no se pudo acceder"
        
        # Detectar tipo de archivo
        filename = os.path.basename(file_path)
        es_json = filename.lower().endswith('.json')
        
        # Leer el contenido del archivo
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                contenido = f.read()
        except UnicodeDecodeError:
            # Intentar con diferentes codificaciones
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    contenido = f.read()
            except Exception as e:
                return f"❌ Error al leer el archivo: {str(e)}"
        except Exception as e:
            return f"❌ Error al leer el archivo: {str(e)}"
        
        if not contenido or not contenido.strip():
            return "❌ Error: El archivo está vacío"
        
        # Si es JSON, validar y procesar
        if es_json:
            try:
                datos_json = json.loads(contenido)
                # Validar estructura básica
                if not isinstance(datos_json, list):
                    return "❌ Error: El JSON debe ser un array de objetos"
                
                # Preparar el payload para n8n con datos JSON
                payload = {
                    "file_content": contenido,
                    "filename": filename,
                    "file_type": "json",
                    "data": datos_json  # Incluir los datos parseados también
                }
            except json.JSONDecodeError as e:
                return f"❌ Error: El archivo JSON no es válido: {str(e)}"
        else:
            # Preparar el payload para n8n con archivo de texto
            payload = {
                "file_content": contenido,
                "filename": filename,
                "file_type": "txt"
            }
        
        # Hacer POST a n8n
        try:
            response = requests.post(
                url_limpia,
                json=payload,
                timeout=30,
                headers={"Content-Type": "application/json"}
            )
            
            # Verificar respuesta
            if response.status_code == 200:
                try:
                    result = response.json()
                    tipo_archivo = "JSON" if es_json else "TXT"
                    return f"✅ Archivo {tipo_archivo} procesado exitosamente\n\nURL: {url_limpia}\nArchivo: {filename}\n\nRespuesta de n8n:\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                except:
                    return f"✅ Archivo procesado exitosamente\n\nURL: {url_limpia}\nArchivo: {filename}\n\nRespuesta de n8n:\n{response.text}"
            else:
                error_msg = f"❌ Error al enviar a n8n (código {response.status_code})\n\nURL: {url_limpia}\nArchivo: {filename}"
                try:
                    error_detail = response.json()
                    error_msg += f"\n\nDetalle: {error_detail}"
                except:
                    error_msg += f"\n\nRespuesta: {response.text}"
                return error_msg
                
        except requests.exceptions.Timeout:
            return f"❌ Error: Timeout al conectar con n8n en {url_limpia}"
        except requests.exceptions.ConnectionError:
            return f"❌ Error: No se pudo conectar con n8n en {url_limpia}\n\nVerifica que n8n esté corriendo y que la URL sea correcta."
        except Exception as e:
            error_msg = f"❌ Error al enviar a n8n: {str(e)}\n\nURL: {url_limpia}"
            if DEBUG:
                import traceback
                error_msg += f"\n\n{traceback.format_exc()}"
            return error_msg
            
    except Exception as e:
        error_msg = f"❌ Error al procesar archivo: {str(e)}"
        if DEBUG:
            import traceback
            error_msg += f"\n\n{traceback.format_exc()}"
        return error_msg

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
        
        # Pestaña 3: Subir archivo WhatsApp
        with gr.Tab("📱 Subir WhatsApp"):
            gr.Markdown("### Subir archivo de WhatsApp")
            gr.Markdown("Sube un archivo de texto (.txt) o JSON (.json) exportado de WhatsApp para procesarlo con n8n")
            
            # JavaScript para manejar localStorage - se ejecuta después de que se renderice el componente
            gr.HTML("""
            <script>
            (function() {
                const STORAGE_KEY = 'n8n_webhook_url';
                let urlInputFound = false;
                
                function setupUrlStorage() {
                    if (urlInputFound) return;
                    
                    // Buscar el input de URL usando el placeholder o label
                    const allInputs = document.querySelectorAll('input[type="text"], textarea');
                    
                    for (let input of allInputs) {
                        // Buscar el contenedor padre que tiene el label
                        let container = input.closest('.form, .form-group, .block, [class*="form"]');
                        if (!container) container = input.parentElement;
                        
                        // Buscar el label en el contenedor o cerca
                        let label = container.querySelector('label');
                        if (!label) {
                            // Buscar en elementos hermanos
                            let sibling = input.previousElementSibling;
                            while (sibling && !label) {
                                if (sibling.tagName === 'LABEL' || sibling.querySelector('label')) {
                                    label = sibling.tagName === 'LABEL' ? sibling : sibling.querySelector('label');
                                }
                                sibling = sibling.previousElementSibling;
                            }
                        }
                        
                        if (label) {
                            const labelText = label.textContent || label.innerText || '';
                            if (labelText.includes('URL de n8n') || labelText.includes('webhook') || 
                                input.placeholder.includes('webhook') || input.placeholder.includes('n8n')) {
                                
                                urlInputFound = true;
                                
                                // Cargar URL guardada al inicio
                                const savedUrl = localStorage.getItem(STORAGE_KEY);
                                if (savedUrl) {
                                    input.value = savedUrl;
                                    // Disparar eventos para que Gradio detecte el cambio
                                    const events = ['input', 'change', 'blur'];
                                    events.forEach(eventType => {
                                        input.dispatchEvent(new Event(eventType, { bubbles: true, cancelable: true }));
                                    });
                                }
                                
                                // Guardar cuando cambia el valor
                                const saveUrl = function() {
                                    const value = this.value ? this.value.trim() : '';
                                    if (value) {
                                        localStorage.setItem(STORAGE_KEY, value);
                                    }
                                };
                                
                                input.addEventListener('input', saveUrl);
                                input.addEventListener('blur', saveUrl);
                                input.addEventListener('change', saveUrl);
                                
                                break;
                            }
                        }
                    }
                }
                
                // Intentar configurar inmediatamente
                setupUrlStorage();
                
                // También intentar después de un delay para cuando Gradio renderice
                setTimeout(setupUrlStorage, 500);
                setTimeout(setupUrlStorage, 1500);
                
                // Observar cambios en el DOM
                const observer = new MutationObserver(function() {
                    if (!urlInputFound) {
                        setupUrlStorage();
                    }
                });
                
                if (document.body) {
                    observer.observe(document.body, { 
                        childList: true, 
                        subtree: true,
                        attributes: false
                    });
                } else {
                    document.addEventListener('DOMContentLoaded', function() {
                        observer.observe(document.body, { 
                            childList: true, 
                            subtree: true,
                            attributes: false
                        });
                    });
                }
            })();
            </script>
            """)
            
            with gr.Row():
                with gr.Column():
                    n8n_url_input = gr.Textbox(
                        label="URL de n8n Webhook",
                        placeholder="Ej: http://localhost:5678/webhook/data_test o https://n8npozos.magoreal.com/webhook/data_test",
                        lines=1,
                        value=N8N_URL  # Valor por defecto desde configuración
                    )
                    gr.Markdown("💾 La URL se guarda automáticamente en tu navegador (localStorage)")
            
            archivo_input = gr.File(
                label="Archivo de WhatsApp (TXT o JSON)",
                file_types=[".txt", ".json"],
                type="filepath"
            )
            
            procesar_btn = gr.Button("🚀 Procesar y Enviar a n8n", variant="primary")
            resultado_whatsapp = gr.Textbox(
                label="Resultado",
                interactive=False,
                lines=10
            )
            
            procesar_btn.click(
                fn=procesar_archivo_whatsapp,
                inputs=[archivo_input, n8n_url_input],
                outputs=[resultado_whatsapp]
            )

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=GRADIO_SERVER_PORT,
        root_path=GRADIO_ROOT_PATH,
        auth=(GRADIO_AUTH_USERNAME, GRADIO_AUTH_PASSWORD),
        share=False,
        show_error=DEBUG
    )
