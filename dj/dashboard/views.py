from django.shortcuts import render
from .n8n_service import N8nService

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
        'executions': executions, # Recent executions
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
