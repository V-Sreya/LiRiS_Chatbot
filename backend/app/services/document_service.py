import io
import re
from typing import Optional

import chromadb
from chromadb.utils import embedding_functions
from pypdf import PdfReader

from app.core.config import settings
from app.services.ocr_service import ocr_service

DOCS_COLLECTION = "user_documents"
CHUNK_SIZE = 600
CHUNK_OVERLAP = 100


def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            cut = text.rfind(". ", start, end)
            if cut == -1 or cut <= start + size // 2:
                cut = end
            else:
                cut += 1
            chunks.append(text[start:cut].strip())
            start = max(cut - overlap, start + 1)
        else:
            chunks.append(text[start:end].strip())
            break
    return [c for c in chunks if c]


def _extract_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(pages)


def _extract_text_file(file_bytes: bytes) -> str:
    for enc in ("utf-8", "utf-16", "latin-1"):
        try:
            return file_bytes.decode(enc)
        except UnicodeDecodeError:
            continue
    return file_bytes.decode("utf-8", errors="replace")


def _extract_image(file_bytes: bytes) -> str:
    res = ocr_service.process_document(file_bytes)
    if res.get("success"):
        return res.get("raw_text", "") or ""
    return ""


def extract_text(file_bytes: bytes, content_type: str, filename: str) -> tuple[str, str]:
    """Return (extracted_text, kind) where kind ∈ {pdf, image, text, unknown}."""
    name = (filename or "").lower()
    ct = (content_type or "").lower()
    if ct == "application/pdf" or name.endswith(".pdf"):
        return _extract_pdf(file_bytes), "pdf"
    if ct.startswith("image/") or name.endswith((".png", ".jpg", ".jpeg", ".webp")):
        return _extract_image(file_bytes), "image"
    if ct.startswith("text/") or name.endswith((".txt", ".md", ".csv", ".json", ".log")):
        return _extract_text_file(file_bytes), "text"
    return _extract_text_file(file_bytes), "unknown"


class DocumentService:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        self.collection = self.client.get_or_create_collection(
            name=DOCS_COLLECTION, embedding_function=self.embedding_fn
        )

    def index_document(
        self,
        session_id: str,
        file_id: int,
        filename: str,
        text: str,
    ) -> int:
        chunks = _chunk_text(text)
        if not chunks:
            return 0
        ids = [f"sess_{session_id}_file_{file_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "session_id": session_id,
                "file_id": file_id,
                "filename": filename,
                "chunk_index": i,
            }
            for i in range(len(chunks))
        ]
        self.collection.upsert(documents=chunks, metadatas=metadatas, ids=ids)
        return len(chunks)

    def query(self, session_id: str, query_text: str, n_results: int = 4):
        try:
            count = self.collection.count()
        except Exception:
            count = 0
        if count == 0:
            return []
        n = min(n_results, count)
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n,
            where={"session_id": session_id},
        )
        out = []
        docs = results.get("documents") or [[]]
        metas = results.get("metadatas") or [[]]
        dists = results.get("distances") or [[]]
        for i in range(len(docs[0])):
            out.append(
                {
                    "content": docs[0][i],
                    "metadata": metas[0][i],
                    "distance": dists[0][i] if dists and dists[0] else None,
                }
            )
        return out

    def has_documents(self, session_id: str) -> bool:
        try:
            res = self.collection.get(where={"session_id": session_id}, limit=1)
            return bool(res and res.get("ids"))
        except Exception:
            return False


document_service = DocumentService()
