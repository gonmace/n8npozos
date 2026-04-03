import base64
import json
import os
import subprocess
import threading
import uuid
from pathlib import Path
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from dashboard.n8n_service import N8nService

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BASE_DIR / 'scripts'
CHATS_DIR = BASE_DIR / 'chats'

# In-memory job store: job_id -> {'lines': [], 'running': bool, 'ok': None|bool}
_script_jobs = {}


def _encode_prompt(s):
    """Encode prompt for safe HTML attribute; preserves newlines and spaces for n8n."""
    raw = (s or '').encode('utf-8')
    return base64.b64encode(raw).decode('ascii')


def audit_index(request):
    service = N8nService()
    records = service.get_audit_records()
    for r in records:
        r['prompt_inicial_b64'] = _encode_prompt(r.get('prompt_inicial'))
        r['prompt_ajuste_b64'] = _encode_prompt(r.get('prompt_ajuste'))

    total = len(records)
    avg_score = round(
        sum(r.get('score_global') or 0 for r in records) / total, 1
    ) if total else 0

    score_counts = {'excelente': 0, 'buena': 0, 'aceptable': 0, 'deficiente': 0}
    for r in records:
        ev = (r.get('evaluacion') or '').lower()
        if ev in score_counts:
            score_counts[ev] += 1

    ajustar_count = sum(1 for r in records if r.get('ajustar_workflow'))

    record_ids = [str(r.get('id')) for r in records if r.get('id')]
    from django.conf import settings
    context = {
        'records': records,
        'record_ids_json': json.dumps(record_ids),
        'workflow_prompt_id': getattr(settings, 'N8N_WORKFLOW_PROMPT_ID', ''),
        'stats': {
            'total': total,
            'avg_score': avg_score,
            'excelente': score_counts['excelente'],
            'buena': score_counts['buena'],
            'aceptable': score_counts['aceptable'],
            'deficiente': score_counts['deficiente'],
            'ajustar': ajustar_count,
        },
    }
    return render(request, 'audit/index.html', context)


@require_POST
def audit_update_prompt(request):
    """Update prompt_ajuste for an audit row. Expects JSON: { row_id, prompt_ajuste }.
    prompt_ajuste must preserve newlines and spaces for n8n workflow prompts."""
    try:
        data = json.loads(request.body)
        row_id = data.get('row_id')
        prompt_ajuste = data.get('prompt_ajuste') or ''
    except (json.JSONDecodeError, TypeError) as e:
        return JsonResponse({'ok': False, 'error': f'JSON inválido: {e}'}, status=400)
    if not row_id:
        return JsonResponse({'ok': False, 'error': 'row_id requerido'}, status=400)
    try:
        service = N8nService()
        ok, err = service.update_audit_row(str(row_id), prompt_ajuste)
        if ok:
            return JsonResponse({'ok': True})
        return JsonResponse({'ok': False, 'error': err or 'Error al guardar en n8n'}, status=500)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@require_POST
def audit_update_node_prompt(request):
    """Update prompt in DataTable and in the n8n workflow node. Expects JSON: { row_id, prompt_ajuste [, workflow_id, node_id ] }.
    node_id viene de la columna nodo_ajuste_id de la tabla de auditoría."""
    try:
        data = json.loads(request.body)
        row_id = data.get('row_id')
        prompt_ajuste = data.get('prompt_ajuste') or ''
        workflow_id = data.get('workflow_id') or ''
        node_id = data.get('node_id') or ''
    except (json.JSONDecodeError, TypeError) as e:
        return JsonResponse({'ok': False, 'error': f'JSON inválido: {e}'}, status=400)
    if not row_id:
        return JsonResponse({'ok': False, 'error': 'row_id requerido'}, status=400)

    from django.conf import settings
    workflow_id = workflow_id or getattr(settings, 'N8N_WORKFLOW_PROMPT_ID', '')

    try:
        service = N8nService()
        # 1. Guardar en DataTable
        ok, err = service.update_audit_row(str(row_id), prompt_ajuste)
        if not ok:
            return JsonResponse({'ok': False, 'error': err or 'Error al guardar en tabla'}, status=500)

        # 2. Actualizar nodo del workflow (node_id = nodo_ajuste_id del registro)
        if workflow_id and node_id:
            ok, err = service.update_workflow_node_prompt(workflow_id, str(node_id), prompt_ajuste)
            if not ok:
                return JsonResponse({'ok': False, 'error': err or 'Error al actualizar nodo en n8n'}, status=500)
        else:
            return JsonResponse({
                'ok': False,
                'error': 'Falta workflow_id o nodo_ajuste_id en el registro'
            }, status=400)

        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


def audit_list_chats(request):
    """Lista archivos .txt y .json en la carpeta chats/."""
    result = {'txt': [], 'json': []}
    if CHATS_DIR.exists():
        result['txt'] = sorted(f.name for f in CHATS_DIR.glob('*.txt'))
        result['json'] = sorted(f.name for f in CHATS_DIR.glob('*.json'))
    return JsonResponse(result)


def audit_preview_json(request):
    """Devuelve los items de un archivo JSON de chats. GET con ?archivo=filename."""
    archivo = request.GET.get('archivo', '')
    if not archivo:
        return JsonResponse({'ok': False, 'error': 'archivo requerido'}, status=400)
    chat_file = (CHATS_DIR / archivo).resolve()
    if not str(chat_file).startswith(str(CHATS_DIR.resolve())):
        return JsonResponse({'ok': False, 'error': 'Ruta inválida'}, status=400)
    if not chat_file.exists():
        return JsonResponse({'ok': False, 'error': 'Archivo no encontrado'}, status=404)
    try:
        with open(chat_file, 'r', encoding='utf-8') as f:
            items = json.load(f)
        return JsonResponse({'ok': True, 'items': items})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


def audit_script_send_select(request):
    """Página de selección de consultas antes de ejecutar envío desde JSON."""
    archivo = request.GET.get('archivo', '')
    if not archivo:
        from django.http import Http404
        raise Http404
    chat_file = (CHATS_DIR / archivo).resolve()
    if not str(chat_file).startswith(str(CHATS_DIR.resolve())) or not chat_file.exists():
        from django.http import Http404
        raise Http404
    return render(request, 'audit/script_send_select.html', {
        'archivo': archivo,
        'prueba': request.GET.get('prueba', ''),
        'url': request.GET.get('url', ''),
        'timeout': request.GET.get('timeout', '120'),
    })


@require_POST
def audit_run_selected(request):
    """Ejecuta el script de envío con los índices seleccionados del JSON."""
    try:
        data = json.loads(request.body)
        archivo = data.get('archivo', '')
        selected_indices = data.get('selected_indices', [])
        prueba = data.get('prueba', False)
        url = data.get('url', '').strip()
        try:
            timeout = min(int(data.get('timeout', 120)), 300)
        except (ValueError, TypeError):
            timeout = 120
    except (json.JSONDecodeError, TypeError) as e:
        return JsonResponse({'ok': False, 'error': f'JSON inválido: {e}'}, status=400)

    if not archivo:
        return JsonResponse({'ok': False, 'error': 'archivo requerido'}, status=400)

    chat_file = (CHATS_DIR / archivo).resolve()
    if not str(chat_file).startswith(str(CHATS_DIR.resolve())):
        return JsonResponse({'ok': False, 'error': 'Ruta inválida'}, status=400)
    if not chat_file.exists():
        return JsonResponse({'ok': False, 'error': 'Archivo no encontrado'}, status=404)

    try:
        with open(chat_file, 'r', encoding='utf-8') as f:
            all_items = json.load(f)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': f'Error al leer archivo: {e}'}, status=500)

    selected_items = [all_items[i] for i in selected_indices if 0 <= i < len(all_items)]
    if not selected_items:
        return JsonResponse({'ok': False, 'error': 'No hay items seleccionados'}, status=400)

    temp_name = f'_temp_{uuid.uuid4().hex}.json'
    temp_file = CHATS_DIR / temp_name
    try:
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(selected_items, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': f'Error al crear archivo temporal: {e}'}, status=500)

    cmd = ['python', '-u', str(SCRIPTS_DIR / 'enviar_mensajes_chatbot.py'), str(temp_file)]
    if prueba:
        cmd.append('--prueba')
    if url:
        cmd += ['--url', url]
    cmd += ['--timeout', str(timeout)]

    job_id = str(uuid.uuid4())
    _script_jobs[job_id] = {'lines': [], 'running': True, 'ok': None, 'proc': None, 'script': 'send'}

    def _run():
        try:
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(BASE_DIR),
                bufsize=1,
                env=env,
            )
            _script_jobs[job_id]['proc'] = proc
            for line in iter(proc.stdout.readline, ''):
                _script_jobs[job_id]['lines'].append(line)
            proc.stdout.close()
            proc.wait(timeout=360)
            _script_jobs[job_id]['ok'] = proc.returncode == 0
        except Exception as e:
            _script_jobs[job_id]['lines'].append(f'\nError: {e}\n')
            _script_jobs[job_id]['ok'] = False
        finally:
            _script_jobs[job_id]['running'] = False
            _script_jobs[job_id]['proc'] = None
            try:
                temp_file.unlink()
            except Exception:
                pass

    threading.Thread(target=_run, daemon=True).start()
    return JsonResponse({'ok': True, 'job_id': job_id})


@require_POST
def audit_run_script(request):
    """Ejecuta un script de la carpeta scripts/. Expects JSON con { script, params }."""
    try:
        data = json.loads(request.body)
        script_name = data.get('script')
        params = data.get('params', {})
    except (json.JSONDecodeError, TypeError) as e:
        return JsonResponse({'ok': False, 'error': f'JSON inválido: {e}'}, status=400)

    cmd = None

    if script_name == 'parse':
        por_archivo = params.get('por_archivo', False)
        archivo = params.get('archivo', '')
        if por_archivo:
            cmd = ['python', '-u', str(SCRIPTS_DIR / 'parse_whatsapp_chats.py'), '--por-archivo']
        elif archivo:
            chat_file = (CHATS_DIR / archivo).resolve()
            if not str(chat_file).startswith(str(CHATS_DIR.resolve())):
                return JsonResponse({'ok': False, 'error': 'Ruta inválida'}, status=400)
            if not chat_file.exists():
                return JsonResponse({'ok': False, 'error': 'Archivo no encontrado'}, status=404)
            cmd = ['python', '-u', str(SCRIPTS_DIR / 'parse_whatsapp_chats.py'), '--archivo', str(chat_file)]
        else:
            return JsonResponse({'ok': False, 'error': 'Falta archivo o por_archivo'}, status=400)

    elif script_name == 'send':
        send_phone = params.get('send_phone', '').strip()
        send_msg = params.get('send_msg', '000').strip() or '000'
        archivo = params.get('archivo', '')
        prueba = params.get('prueba', False)
        url = params.get('url', '').strip()
        try:
            timeout = min(int(params.get('timeout', 120)), 300)
        except (ValueError, TypeError):
            timeout = 120

        cmd = ['python', '-u', str(SCRIPTS_DIR / 'enviar_mensajes_chatbot.py')]

        if send_phone:
            phone = send_phone.replace(' ', '').replace('+', '')
            if not phone.isdigit():
                return JsonResponse({'ok': False, 'error': 'Teléfono debe contener solo dígitos'}, status=400)
            cmd += ['--send', phone, '--mensaje', send_msg]
        elif archivo:
            chat_file = (CHATS_DIR / archivo).resolve()
            if not str(chat_file).startswith(str(CHATS_DIR.resolve())):
                return JsonResponse({'ok': False, 'error': 'Ruta inválida'}, status=400)
            if not chat_file.exists():
                return JsonResponse({'ok': False, 'error': 'Archivo no encontrado'}, status=404)
            cmd.append(str(chat_file))
            if prueba:
                cmd.append('--prueba')
        else:
            return JsonResponse({'ok': False, 'error': 'Falta archivo o teléfono'}, status=400)

        if url:
            cmd += ['--url', url]
        cmd += ['--timeout', str(timeout)]

    else:
        return JsonResponse({'ok': False, 'error': 'Script desconocido'}, status=400)

    job_id = str(uuid.uuid4())
    _script_jobs[job_id] = {'lines': [], 'running': True, 'ok': None, 'proc': None, 'script': script_name}

    def _run():
        try:
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(BASE_DIR),
                bufsize=1,
                env=env,
            )
            _script_jobs[job_id]['proc'] = proc
            for line in iter(proc.stdout.readline, ''):
                _script_jobs[job_id]['lines'].append(line)
            proc.stdout.close()
            proc.wait(timeout=360)
            _script_jobs[job_id]['ok'] = proc.returncode == 0
        except Exception as e:
            _script_jobs[job_id]['lines'].append(f'\nError: {e}\n')
            _script_jobs[job_id]['ok'] = False
        finally:
            _script_jobs[job_id]['running'] = False
            _script_jobs[job_id]['proc'] = None

    threading.Thread(target=_run, daemon=True).start()
    return JsonResponse({'ok': True, 'job_id': job_id})


def audit_script_output(request, job_id):
    """Devuelve la salida acumulada de un job en ejecución."""
    job = _script_jobs.get(job_id)
    if not job:
        return JsonResponse({'error': 'Job no encontrado'}, status=404)
    return JsonResponse({
        'output': ''.join(job['lines']),
        'running': job['running'],
        'ok': job['ok'],
    })


def audit_script_monitor(request, job_id):
    """Página de monitoreo para un job en ejecución."""
    job = _script_jobs.get(job_id)
    if not job:
        from django.http import Http404
        raise Http404
    return render(request, 'audit/script_monitor.html', {
        'job_id': job_id,
        'script_name': job.get('script', ''),
    })


@require_POST
def audit_script_cancel(request, job_id):
    """Cancela un job en ejecución matando el proceso."""
    job = _script_jobs.get(job_id)
    if not job:
        return JsonResponse({'error': 'Job no encontrado'}, status=404)
    if not job.get('running'):
        return JsonResponse({'ok': True, 'msg': 'El job ya terminó'})
    proc = job.get('proc')
    if proc:
        try:
            proc.kill()
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)}, status=500)
    job['running'] = False
    job['ok'] = False
    job['lines'].append('\n[Cancelado por el usuario]\n')
    return JsonResponse({'ok': True})


@require_POST
def audit_delete_rows(request):
    """Delete selected audit rows. Expects JSON: { row_ids: [...] }."""
    try:
        data = json.loads(request.body)
        row_ids = data.get('row_ids') or []
    except (json.JSONDecodeError, TypeError) as e:
        return JsonResponse({'ok': False, 'error': f'JSON inválido: {e}'}, status=400)
    if not row_ids:
        return JsonResponse({'ok': False, 'error': 'row_ids requerido (array)'}, status=400)
    try:
        service = N8nService()
        ok, err = service.delete_audit_rows(row_ids)
        if ok:
            return JsonResponse({'ok': True})
        return JsonResponse({'ok': False, 'error': err or 'Error al borrar en n8n'}, status=500)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)
