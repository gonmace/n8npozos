import json
import docker as docker_sdk
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from .n8n_service import N8nService
from .chromadb_service import ChromaDBService

MCP_CONTAINER = "n8npozos-n8n-mcp"


def _mcp_status():
    try:
        client = docker_sdk.from_env()
        container = client.containers.get(MCP_CONTAINER)
        return container.status  # "running", "exited", etc.
    except docker_sdk.errors.NotFound:
        return "not_found"
    except Exception:
        return "error"


@require_POST
def mcp_toggle(request):
    try:
        client = docker_sdk.from_env()
        container = client.containers.get(MCP_CONTAINER)
        if container.status == "running":
            container.stop(timeout=5)
        else:
            container.start()
        container.reload()
        return JsonResponse({"status": container.status})
    except docker_sdk.errors.NotFound:
        return JsonResponse({"error": f"Contenedor '{MCP_CONTAINER}' no encontrado"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def index(request):
    service = N8nService()
    workflows = service.get_workflows()
    executions = service.get_executions(limit=10)
    
    # Get chat sessions for statistics
    sessions = service.get_chat_sessions()
    total_conversations = len(sessions)
    conversations_with_price = len([s for s in sessions if s.get('precio')])

    # Stats
    total_workflows = len(workflows)
    active_workflows = len([w for w in workflows if w.get('active')])
    inactive_workflows = total_workflows - active_workflows

    context = {
        'workflows': workflows,
        'executions': executions,
        'mcp_status': _mcp_status(),
        'stats': {
            'total': total_workflows,
            'active': active_workflows,
            'inactive': inactive_workflows,
            'total_conversations': total_conversations,
            'conversations_with_price': conversations_with_price
        }
    }
    return render(request, 'dashboard/index.html', context)

def workflow_detail(request, workflow_id):
    service = N8nService()
    workflow = service.get_workflow(workflow_id)
    # Get executions specifically for this workflow if possible,
    # sadly n8n API simple endpoint doesn't always filter easily by workflowId in v1 without extra params,
    # but we will fetch general executions and filter in python for now or use the proper filter if available.
    # Actually, v1/executions supports workflowId filter? Let's assume yes or just show all for now.
    # Refined: We will modify service later if needed, but for now specific execution fetching might require more parsing.
    # Let's just pass the workflow detail for now.
    return render(request, 'dashboard/detail.html', {'workflow': workflow})

def chat_history(request):
    """
    Specific view for the chat history visualization.
    We assume the workflow 'chat_history' contains the relevant data.
    """
    service = N8nService()
    
    # Fetch all sessions (returns list of dicts)
    sessions_data = service.get_chat_sessions()
    
    # Check if a specific session is selected
    active_session_id = request.GET.get('session_id')
    
    # Store sessions in list for the template sidebar
    sessions_list = []
    for session in sessions_data:
        # Extract ID, checking both potential keys
        sid = session.get('sessionId') or session.get('session_id')
        if not sid:
            continue
            
        # Create context dict for template
        session_context = session.copy()
        session_context['id'] = str(sid)
        session_context['active'] = (str(sid) == str(active_session_id))
        
        sessions_list.append(session_context)
        
    # If active session, fetch messages
    active_messages = []
    active_session = None
    if active_session_id:
        active_messages = service.get_session_history(active_session_id)
        for s in sessions_list:
            if s['id'] == str(active_session_id):
                active_session = s
                break

    # Datos para exportar a Markdown (solo type y content)
    chat_export_data = {
        'sessionId': active_session_id or '',
        'messages': [
            {
                'type': m.get('message', {}).get('type', 'ai'),
                'content': m.get('message', {}).get('content', '') or ''
            }
            for m in active_messages
        ]
    }

    context = {
        'sessions': sessions_list,
        'active_session_id': active_session_id,
        'active_session': active_session,
        'messages': active_messages,
        'chat_export_data': chat_export_data
    }

    return render(request, 'dashboard/chat_history.html', context)


# ── ChromaDB views ────────────────────────────────────────────────────────────

def chromadb_index(request):
    svc = ChromaDBService()
    documents = svc.list_documents()
    stats = svc.get_stats(documents)
    return render(request, 'dashboard/chromadb.html', {
        'documents_json': json.dumps(documents, ensure_ascii=False),
        'stats': stats,
        'collection': svc.collection,
        'whatsapp_webhook_default': getattr(settings, 'N8N_WHATSAPP_WEBHOOK', ''),
    })


@require_POST
def chromadb_create(request):
    try:
        data = json.loads(request.body)
        text = data.get('text', '').strip()
        if not text:
            return JsonResponse({'ok': False, 'error': 'El texto no puede estar vacío'})
        svc = ChromaDBService()
        doc_id = svc.create_document(
            text=text,
            categoria=data.get('categoria', '').strip() or None,
            source=data.get('source', '').strip() or None,
        )
        return JsonResponse({'ok': True, 'id': doc_id})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@require_POST
def chromadb_update(request, doc_id):
    try:
        data = json.loads(request.body)
        text = data.get('text', '').strip()
        if not text:
            return JsonResponse({'ok': False, 'error': 'El texto no puede estar vacío'})
        svc = ChromaDBService()
        svc.update_document(
            doc_id=doc_id,
            text=text,
            categoria=data.get('categoria', '').strip() or None,
            source=data.get('source', '').strip() or None,
        )
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@require_POST
def chromadb_delete(request, doc_id):
    try:
        ChromaDBService().delete_document(doc_id)
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@require_POST
def chromadb_bulk_delete(request):
    try:
        data = json.loads(request.body)
        ids = data.get('ids', [])
        if not ids:
            return JsonResponse({'ok': False, 'error': 'No se enviaron IDs'})
        errors = ChromaDBService().bulk_delete(ids)
        deleted = len(ids) - len(errors)
        return JsonResponse({'ok': True, 'deleted': deleted, 'errors': errors})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


def chromadb_get(request, doc_id):
    try:
        doc = ChromaDBService().get_document(doc_id)
        return JsonResponse({'ok': True, 'doc': doc})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=404)


def chromadb_export(request):
    try:
        documents = ChromaDBService().list_documents()
        content = json.dumps(documents, ensure_ascii=False, indent=2)
        response = HttpResponse(content, content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="embeddings.json"'
        return response
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@require_POST
def chromadb_whatsapp(request):
    import requests as req_lib
    try:
        n8n_url = request.POST.get('n8n_url', '').strip()
        if not n8n_url:
            return JsonResponse({'ok': False, 'error': 'URL de n8n es requerida'})
        if not n8n_url.startswith(('http://', 'https://')):
            return JsonResponse({'ok': False, 'error': 'URL inválida'})

        archivo = request.FILES.get('archivo')
        if not archivo:
            return JsonResponse({'ok': False, 'error': 'No se subió ningún archivo'})

        filename = archivo.name
        content = archivo.read().decode('utf-8', errors='replace')
        file_type = 'json' if filename.lower().endswith('.json') else 'txt'

        payload = {'file_content': content, 'filename': filename, 'file_type': file_type}
        if file_type == 'json':
            try:
                payload['data'] = json.loads(content)
            except json.JSONDecodeError as e:
                return JsonResponse({'ok': False, 'error': f'JSON inválido: {e}'})

        r = req_lib.post(n8n_url, json=payload, timeout=30, headers={'Content-Type': 'application/json'})
        if r.status_code == 200:
            try:
                result = r.json()
            except Exception:
                result = r.text
            return JsonResponse({'ok': True, 'result': result})
        return JsonResponse({'ok': False, 'error': f'n8n respondió {r.status_code}: {r.text[:200]}'})
    except req_lib.exceptions.Timeout:
        return JsonResponse({'ok': False, 'error': 'Timeout al conectar con n8n'})
    except req_lib.exceptions.ConnectionError:
        return JsonResponse({'ok': False, 'error': 'No se pudo conectar con n8n'})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)
