import requests
from django.conf import settings


class ChromaDBService:
    def __init__(self):
        self.base_url = settings.CHROMA_API_URL.rstrip('/')
        self.collection = settings.CHROMA_COLLECTION

    def _url(self, path):
        return f"{self.base_url}{path}"

    def list_documents(self):
        try:
            r = requests.get(self._url(f"/collections/{self.collection}/documents"), timeout=15)
            r.raise_for_status()
            return r.json().get("documents", [])
        except requests.exceptions.RequestException as e:
            print(f"ChromaDB list error: {e}")
            return []

    def create_document(self, text, categoria=None, source=None, doc_id=None):
        payload = {"text": text}
        if categoria:
            payload["categoria"] = categoria
        if source:
            payload["source"] = source
        if doc_id:
            payload["doc_id"] = doc_id
        r = requests.post(self._url(f"/collections/{self.collection}/documents"), json=payload, timeout=15)
        r.raise_for_status()
        return r.json()["id"]

    def get_document(self, doc_id):
        r = requests.get(self._url(f"/collections/{self.collection}/documents/{doc_id}"), timeout=15)
        r.raise_for_status()
        return r.json()

    def update_document(self, doc_id, text, categoria=None, source=None):
        payload = {"text": text}
        if categoria:
            payload["categoria"] = categoria
        if source:
            payload["source"] = source
        r = requests.put(self._url(f"/collections/{self.collection}/documents/{doc_id}"), json=payload, timeout=15)
        r.raise_for_status()

    def delete_document(self, doc_id):
        r = requests.delete(self._url(f"/collections/{self.collection}/documents/{doc_id}"), timeout=15)
        r.raise_for_status()

    def bulk_delete(self, doc_ids):
        errors = []
        for doc_id in doc_ids:
            try:
                self.delete_document(doc_id)
            except Exception as e:
                errors.append(str(e))
        return errors

    def get_stats(self, documents=None):
        if documents is None:
            documents = self.list_documents()
        total = len(documents)
        by_category = {}
        for doc in documents:
            cat = (doc.get("metadata") or {}).get("categoria") or "Sin categoría"
            by_category[cat] = by_category.get(cat, 0) + 1
        return {"total": total, "by_category": by_category}
