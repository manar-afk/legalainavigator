from typing import Dict, List, Optional
import threading
from ..models.document import DocumentMeta, DocumentChunk


class InMemoryDocumentStore:
    """
    Thread-safe in-memory document store.
    Preserves:
      1. Authentic extracted text (raw_texts) without modification.
      2. Original uploaded file payload (raw_bytes) retained separately for binary integrity and audit.
      3. Structural section chunks (chunks) preserving exact character/paragraph spans.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._documents: Dict[str, DocumentMeta] = {}
        self._chunks: Dict[str, List[DocumentChunk]] = {}  # doc_id -> chunks
        self._raw_texts: Dict[str, str] = {}              # doc_id -> full authentic extracted text
        self._raw_bytes: Dict[str, bytes] = {}            # doc_id -> original uploaded binary payload

    def add_document(
        self,
        meta: DocumentMeta,
        raw_text: str,
        chunks: List[DocumentChunk],
        raw_bytes: Optional[bytes] = None
    ) -> str:
        with self._lock:
            self._documents[meta.doc_id] = meta
            self._raw_texts[meta.doc_id] = raw_text
            self._chunks[meta.doc_id] = chunks
            if raw_bytes is not None:
                self._raw_bytes[meta.doc_id] = raw_bytes
            return meta.doc_id

    def get_document(self, doc_id: str) -> Optional[DocumentMeta]:
        with self._lock:
            return self._documents.get(doc_id)

    def get_raw_text(self, doc_id: str) -> Optional[str]:
        with self._lock:
            return self._raw_texts.get(doc_id)

    def get_raw_bytes(self, doc_id: str) -> Optional[bytes]:
        with self._lock:
            return self._raw_bytes.get(doc_id)

    def get_chunks(self, doc_id: str) -> List[DocumentChunk]:
        with self._lock:
            return list(self._chunks.get(doc_id, []))

    def get_all_chunks(self, doc_ids: Optional[List[str]] = None) -> List[DocumentChunk]:
        with self._lock:
            if not doc_ids:
                all_chunks = []
                for chunk_list in self._chunks.values():
                    all_chunks.extend(chunk_list)
                return all_chunks
            selected = []
            for did in doc_ids:
                if did in self._chunks:
                    selected.extend(self._chunks[did])
            return selected

    def list_documents(self) -> List[DocumentMeta]:
        with self._lock:
            return list(self._documents.values())

    def delete_document(self, doc_id: str) -> bool:
        with self._lock:
            if doc_id in self._documents:
                del self._documents[doc_id]
                self._chunks.pop(doc_id, None)
                self._raw_texts.pop(doc_id, None)
                self._raw_bytes.pop(doc_id, None)
                return True
            return False

    def clear(self):
        with self._lock:
            self._documents.clear()
            self._chunks.clear()
            self._raw_texts.clear()
            self._raw_bytes.clear()


# Global singleton instance
document_store = InMemoryDocumentStore()
