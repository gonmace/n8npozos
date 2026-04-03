import json
from urllib.parse import quote

import requests
from django.conf import settings

class N8nService:
    def __init__(self):
        self.api_key = settings.N8N_API_KEY
        self.base_url = settings.N8N_URL

        if not self.api_key:
            raise ValueError("N8N_API_KEY is not set in settings")
        if not self.base_url:
            raise ValueError("N8N_URL is not set in settings")

    def _get_headers(self):
        return {
            "X-N8N-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }

    def get_workflows(self):
        """
        Fetch all workflows from n8n.
        """
        url = f"{self.base_url}/api/v1/workflows"
        try:
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            return response.json().get('data', [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching workflows: {e}")
            return []

    def get_executions(self, limit=20, include_data=False):
        """
        Fetch recent executions.
        """
        url = f"{self.base_url}/api/v1/executions"
        params = {"limit": limit, "includeData": str(include_data).lower()}
        try:
            response = requests.get(url, headers=self._get_headers(), params=params)
            response.raise_for_status()
            return response.json().get('data', [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching executions: {e}")
            return []

    def get_workflow(self, id):
        """
        Fetch a single workflow by ID.
        """
        url = f"{self.base_url}/api/v1/workflows/{id}"
        try:
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching workflow {id}: {e}")
            return None

    def _execute_workflow(self, workflow_id, payload=None):
        """
        Helper to execute a workflow via API and return the output of the last node.
        """
        url = f"{self.base_url}/api/v1/workflows/{workflow_id}/execute"
        try:
            # Payload structure for execute endpoint
            # It expects { "executionData": { "workflowData": { ... }, "nodeData": { ... } } } ???
            # Actually standard POST /execute just takes body if using manual trigger?
            # Or { "formData": ... } ?
            # n8n API v1 /execute documentation says:
            # Body: { "executionData": { "json": {}, "binary": {} } } for Start Node?
            # Or just raw JSON if the workflow starts with a Webhook/Trigger?
            # For Manual Trigger, it might be simpler.
            # Let's try standard POST with no body for list, and body for lookup.
            
            # Simple wrapper to trigger
            req_data = {}
            if payload:
                 # If we want to pass input data to the workflow (e.g., to Manual Trigger or Webhook node used as start)
                 # We likely need to map it to what n8n expects.
                 # For core-get-session-history, we used $json.query.sessionId in Webhook.
                 # If we switch to Manual Trigger or just simple execution, we might need to access parameters differently.
                 # SAFE BET: Pass it as "executionData".
                 # But real world n8n API often just runs it.
                 # Let's try just passing the payload if we used a Webhook-compatible manual trigger?
                 # No, let's stick to the /webhook/ URL for passing data IF it worked.
                 # Since we use /execute, we are effectively running "Manual".
                 # The "Postgres" node in `core_get_session_history` uses `{{ $json.query.sessionId }}`.
                 # This `$json` comes from the Trigger.
                 # If we use /execute, the input to the first node is what we send.
                 # So we should send { "query": { "sessionId": "..." } } as the input JSON.
                 pass
            
            # Note: Requests to /execute trigger a run and wait.
            # We need to send correct body structure.
            # { "message": "..." } -> available as $json.message
            response = requests.post(url, headers=self._get_headers(), json=payload)
            response.raise_for_status()
            
            # Parse execution result
            # Structure: { data: { resultData: { runData: { "NodeName": [{ data: { main: [[ { json: ... } ]] } }] } } } }
            resp_json = response.json()
            
            # We need to find the output data. 
            # We can look for the "Postgres" node or "Respond to Webhook" node data.
            run_data = resp_json.get('data', {}).get('resultData', {}).get('runData', {})
            
            # Try to get data from "Respond to Webhook" or "Postgres"
            output_node = run_data.get('Respond to Webhook') or run_data.get('Postgres')
            if not output_node:
                 # Fallback to any node that has output
                 for node_name, node_runs in run_data.items():
                     if node_runs:
                         output_node = node_runs
                         break
            
            if output_node and len(output_node) > 0:
                # Assuming first run of the node [0]
                # data.main[0][0].json
                try:
                    items = output_node[0].get('data', {}).get('main', [])[0]
                    return [item.get('json', {}) for item in items]
                except (IndexError, AttributeError):
                    return []
            return []

        except requests.exceptions.RequestException as e:
            print(f"Error executing workflow {workflow_id}: {e}")
            try:
                print(e.response.text)
            except:
                pass
            return []

    # DataTable IDs (from n8n workflow inspection)
    CLIENTES_TABLE_ID = "0zB8nzU75uBn6rRp"
    STATE_TABLE_ID = "mKLOfijuNXAa8MZi"
    PROJECT_ID = "D5S4DzsCuzzjBHo5"
    CHAT_HISTORY_WORKFLOW_ID = "6e8MOq0WC6a2OKQh"
    AUDIT_TABLE_ID = "kL9BzTmpuJiuPxh6"

    def _get_datatable_rows(self, table_id, filters=None, limit=200, sort_by=None):
        """
        Fetch rows from an n8n DataTable via REST API.
        Uses GET /api/v1/data-tables/{tableId}/rows
        sort_by: e.g. "createdAt:desc" for newest first
        """
        url = f"{self.base_url}/api/v1/data-tables/{table_id}/rows"
        params = {"limit": limit}
        if filters:
            params.update(filters)
        if sort_by:
            params["sortBy"] = sort_by
        try:
            response = requests.get(url, headers=self._get_headers(), params=params)
            response.raise_for_status()
            data = response.json()
            # n8n returns { data: [...] } or just [...]
            if isinstance(data, list):
                return data
            return data.get('data', data.get('rows', []))
        except requests.exceptions.RequestException as e:
            print(f"Error fetching datatable {table_id}: {e}")
            try:
                print(e.response.text if hasattr(e, 'response') and e.response else '')
            except Exception:
                pass
            return []

    def get_chat_sessions(self):
        """
        Fetch all sessions by joining pozos_clientes + pozos_state DataTables.
        Returns list of dicts with session info (session_id, telefono, contacto,
        precio, state, etc.).
        """
        clientes = self._get_datatable_rows(self.CLIENTES_TABLE_ID)
        states = self._get_datatable_rows(self.STATE_TABLE_ID)

        # Build a lookup dict by session_id from states
        state_map = {s.get('session_id'): s for s in states if s.get('session_id')}

        sessions = []
        for row in clientes:
            sid = row.get('session_id')
            if not sid:
                continue
            state_row = state_map.get(sid, {})
            sessions.append({
                'session_id': sid,
                'sessionId': sid,  # alias for template compatibility
                'telefono': row.get('telefono', ''),
                'contacto': row.get('contacto', ''),
                'precio': row.get('precio'),
                'fecha_precio': row.get('fecha_precio'),
                'dist_from_scz': row.get('dist_from_scz'),
                'state': state_row.get('state', ''),
                'resumen': state_row.get('resumen', ''),
            })

        # Sort by most recent first (by fecha_precio if available)
        sessions.sort(key=lambda s: s.get('fecha_precio') or '', reverse=True)
        return sessions

    def _list_data_tables(self):
        """List all DataTables available in n8n."""
        url = f"{self.base_url}/api/v1/data-tables"
        try:
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                return data
            return data.get('data', [])
        except requests.exceptions.RequestException as e:
            print(f"Error listing data tables: {e}")
            return []

    def get_audit_records(self, limit=100):
        """
        Fetch records from the auditoria DataTable.
        Uses AUDIT_TABLE_ID with sortBy=createdAt:desc.
        """
        rows = self._get_datatable_rows(
            self.AUDIT_TABLE_ID,
            limit=limit,
            sort_by="createdAt:desc"
        )
        return rows

    def update_audit_row(self, row_id, prompt_ajuste):
        """
        Update prompt_ajuste for a row in the auditoria DataTable.
        Uses n8n API v1: PATCH /data-tables/{id}/rows/update with filter + data.
        prompt_ajuste is sent as-is to preserve newlines and spaces for n8n workflow prompts.
        Returns (success: bool, error_message: str|None).
        """
        base = self.base_url.rstrip('/')
        headers = self._get_headers()
        tid = self.AUDIT_TABLE_ID
        pid = self.PROJECT_ID

        # Formato oficial n8n API v1 (openapi): filter + data
        payload = {
            "filter": {
                "type": "and",
                "filters": [
                    {"columnName": "id", "condition": "eq", "value": row_id}
                ],
            },
            "data": {"prompt_ajuste": prompt_ajuste},
            "returnData": False,
        }

        urls = [
            f"{base}/api/v1/data-tables/{tid}/rows/update",
            f"{base}/api/v1/projects/{pid}/data-tables/{tid}/rows/update",
        ]
        last_err = None
        for url in urls:
            try:
                r = requests.patch(url, headers=headers, json=payload, timeout=15)
                if r.status_code == 200:
                    return True, None
                try:
                    err = r.json()
                    last_err = err.get("message", err.get("error", str(err)[:300]))
                except Exception:
                    last_err = f"{r.status_code}: {r.text[:300]}"
            except requests.exceptions.RequestException as e:
                last_err = str(e)

        # Fallback: webhook si la API no tiene acceso (ej. plan free trial)
        webhook_url = getattr(settings, 'N8N_WEBHOOK_UPDATE_AUDIT_PROMPT', '') or ''
        if webhook_url:
            try:
                r = requests.post(
                    webhook_url,
                    headers={**headers, "Content-Type": "application/json"},
                    json={"row_id": row_id, "prompt_ajuste": prompt_ajuste},
                    timeout=15,
                )
                if r.status_code in (200, 201, 204):
                    return True, None
                last_err = f"Webhook {r.status_code}: {r.text[:200]}"
            except requests.exceptions.RequestException as e:
                last_err = str(e)

        return False, last_err or "n8n API no aceptó la actualización"

    def update_workflow_node_prompt(self, workflow_id, node_id, prompt):
        """
        Update the system prompt of a node in an n8n workflow.
        GET workflow, find node by id (nodo_ajuste_id), update parameters.systemMessage (or options.systemMessage
        or messages with role=system), PUT workflow back.
        Returns (success: bool, error_message: str|None).
        """
        if not workflow_id or not node_id:
            return False, "workflow_id y node_id requeridos"
        base = self.base_url.rstrip('/')
        headers = self._get_headers()

        # Webhook fallback
        webhook_url = getattr(settings, 'N8N_WEBHOOK_UPDATE_PROMPT_NODE', '') or ''
        if webhook_url:
            try:
                r = requests.post(
                    webhook_url,
                    headers={**headers, "Content-Type": "application/json"},
                    json={"workflow_id": workflow_id, "node_id": node_id, "prompt": prompt},
                    timeout=30,
                )
                if r.status_code in (200, 201, 204):
                    return True, None
                return False, f"Webhook {r.status_code}: {r.text[:200]}"
            except requests.exceptions.RequestException as e:
                return False, str(e)

        # GET workflow
        url_get = f"{base}/api/v1/workflows/{workflow_id}"
        try:
            r = requests.get(url_get, headers=headers, timeout=15)
            if r.status_code != 200:
                try:
                    err = r.json()
                    return False, err.get("message", err.get("error", f"{r.status_code}: {r.text[:200]}"))
                except Exception:
                    return False, f"{r.status_code}: {r.text[:200]}"
            resp = r.json()
            workflow = resp.get("data", resp)
        except requests.exceptions.RequestException as e:
            return False, str(e)

        nodes = workflow.get("nodes") or []
        node_found = None
        for n in nodes:
            if n.get("id") == node_id or str(n.get("id")) == str(node_id):
                node_found = n
                break

        if not node_found:
            return False, f"Nodo '{node_id}' no encontrado en el workflow"

        params = node_found.get("parameters") or {}
        updated = False

        # systemMessage directo (OpenAI, etc.) - valor fijo
        if "systemMessage" in params:
            params["systemMessage"] = prompt
            updated = True
        # options.systemMessage (algunos nodos LangChain)
        if "options" in params and isinstance(params["options"], dict):
            opts = params["options"]
            if "systemMessage" in opts:
                opts["systemMessage"] = prompt
                updated = True
        # messages array (algunos nodos usan messages: [{role: "system", content: "..."}])
        if "messages" in params and isinstance(params["messages"], (list, dict)):
            msgs = params["messages"]
            if isinstance(msgs, dict) and "values" in msgs:
                for v in msgs.get("values", []):
                    if v.get("role") == "system":
                        v["content"] = prompt
                        updated = True
                        break
            elif isinstance(msgs, list):
                for m in msgs:
                    if isinstance(m, dict) and m.get("role") == "system":
                        m["content"] = prompt
                        updated = True
                        break
        # text/options.text como fallback
        if not updated and "text" in params:
            params["text"] = prompt
            updated = True

        if not updated:
            params["systemMessage"] = prompt
            updated = True

        node_found["parameters"] = params

        # PUT workflow - solo propiedades aceptadas por la API (evitar "additional properties")
        url_put = f"{base}/api/v1/workflows/{workflow_id}"
        put_body = {
            "name": workflow.get("name", ""),
            "nodes": workflow["nodes"],
            "connections": workflow.get("connections", {}),
            "settings": workflow.get("settings", {}),
        }
        # Incluir staticData solo si existe (algunas APIs lo aceptan)
        if workflow.get("staticData") is not None:
            put_body["staticData"] = workflow["staticData"]

        try:
            r = requests.put(url_put, headers=headers, json=put_body, timeout=15)
            if r.status_code == 200:
                return True, None
            try:
                err = r.json()
                return False, err.get("message", err.get("error", str(err)[:300]))
            except Exception:
                return False, f"{r.status_code}: {r.text[:300]}"
        except requests.exceptions.RequestException as e:
            return False, str(e)

    def delete_audit_rows(self, row_ids):
        """
        Delete rows from the auditoria DataTable by id.
        Uses n8n API: DELETE /data-tables/{id}/rows/delete with filter (query param).
        Filter format: JSON string, e.g. {"type":"or","filters":[{"columnName":"id","condition":"eq","value":"x"},...]}
        Returns (success: bool, error_message: str|None).
        """
        if not row_ids:
            return True, None
        base = self.base_url.rstrip('/')
        headers = self._get_headers()
        tid = self.AUDIT_TABLE_ID
        filters = [{"columnName": "id", "condition": "eq", "value": str(rid)} for rid in row_ids]
        filter_obj = {"type": "or", "filters": filters} if len(filters) > 1 else {"type": "and", "filters": filters}
        filter_str = json.dumps(filter_obj)
        filter_encoded = quote(filter_str, safe="")
        url = f"{base}/api/v1/data-tables/{tid}/rows/delete?filter={filter_encoded}"
        try:
            r = requests.delete(url, headers=headers, timeout=15)
            if r.status_code == 200:
                return True, None
            try:
                err = r.json()
                return False, err.get("message", err.get("error", str(err)[:300]))
            except Exception:
                return False, f"{r.status_code}: {r.text[:300]}"
        except requests.exceptions.RequestException as e:
            return False, str(e)

    def get_session_history(self, session_id):
        """
        Fetch chat message history for a session via the workflow's webhook.
        The workflow must expose a webhook at /webhook/get_session_history that accepts
        sessionId as query param and returns [{message: {type, content}}, ...].
        """
        url = f"{self.base_url.rstrip('/')}/webhook/get_session_history"
        params = {"sessionId": session_id}
        try:
            response = requests.get(url, headers=self._get_headers(), params=params, timeout=30)
            if response.status_code == 404:
                return []
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else []
        except requests.exceptions.RequestException as e:
            print(f"Error fetching session history for {session_id}: {e}")
            return []


