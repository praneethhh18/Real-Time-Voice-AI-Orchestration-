"""
Document ingestion: file -> text -> chunks -> embeddings -> vector store.

Supported file types: .pdf, .txt, .md.

Chunking strategy: token-ish character chunks with overlap. We use a simple
recursive splitter (paragraphs -> sentences -> words) instead of pulling in
LangChain just for one helper. ~800 chars per chunk with 120 char overlap is
a good default for short, conversational answers.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader

from app.kb.store import get_collection


CHUNK_SIZE = 800       # characters; rough proxy for ~150-200 tokens
CHUNK_OVERLAP = 120    # carried over to keep context across boundaries


# ---------- text extraction ----------

def _extract_text(file_path: Path) -> str:
    """Read the file and return its plain-text content."""
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(str(file_path))
        return "\n\n".join((page.extract_text() or "") for page in reader.pages)
    if suffix in {".txt", ".md"}:
        return file_path.read_text(encoding="utf-8", errors="ignore")
    raise ValueError(f"Unsupported file type: {suffix}")


# ---------- chunking ----------

def _split_paragraphs(text: str) -> list[str]:
    # Collapse stray whitespace, then split on blank lines.
    text = re.sub(r"[ \t]+", " ", text).strip()
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def _chunk_text(text: str) -> list[str]:
    """
    Split text into ~CHUNK_SIZE-character chunks with overlap.

    We greedily pack paragraphs into a chunk until it exceeds the size,
    then start a new chunk that begins with the tail of the previous one
    (overlap) so semantic context isn't cut mid-thought.
    """
    paragraphs = _split_paragraphs(text)
    chunks: list[str] = []
    buf = ""

    for p in paragraphs:
        # If a single paragraph blows past CHUNK_SIZE, hard-split it.
        if len(p) > CHUNK_SIZE:
            for i in range(0, len(p), CHUNK_SIZE - CHUNK_OVERLAP):
                chunks.append(p[i : i + CHUNK_SIZE])
            continue

        if len(buf) + len(p) + 2 <= CHUNK_SIZE:
            buf = f"{buf}\n\n{p}".strip()
        else:
            if buf:
                chunks.append(buf)
            # carry the tail of the last chunk forward as overlap
            tail = buf[-CHUNK_OVERLAP:] if buf else ""
            buf = (tail + "\n\n" + p).strip()

    if buf:
        chunks.append(buf)
    return chunks


# ---------- public API ----------

def ingest_file(file_path: Path, doc_name: str) -> dict:
    """
    Ingest a file into the vector store. Returns metadata about what was added.

    Each chunk gets a stable UUID-prefixed ID so we can later delete all
    chunks belonging to one document in a single `where` query.
    """
    text = _extract_text(file_path)
    if not text.strip():
        raise ValueError("Document appears to be empty or unreadable.")

    chunks = _chunk_text(text)
    if not chunks:
        raise ValueError("Document produced no chunks.")

    doc_id = str(uuid.uuid4())
    ids = [f"{doc_id}::{i}" for i in range(len(chunks))]
    metadatas = [
        {"doc_id": doc_id, "doc_name": doc_name, "chunk_index": i}
        for i in range(len(chunks))
    ]

    get_collection().add(documents=chunks, ids=ids, metadatas=metadatas)

    return {
        "doc_id": doc_id,
        "doc_name": doc_name,
        "num_chunks": len(chunks),
        "char_count": len(text),
    }


def list_documents() -> list[dict]:
    """List all ingested documents (deduplicated by doc_id) with chunk counts."""
    coll = get_collection()
    # Pull only metadatas — we don't need the text or vectors here.
    # `limit` is set high explicitly so we don't rely on Chroma's default,
    # which has changed between versions and once silently capped to 10.
    result = coll.get(include=["metadatas"], limit=100_000)
    metadatas = result.get("metadatas") or []

    by_doc: dict[str, dict] = {}
    for m in metadatas:
        if not m:
            continue
        did = m.get("doc_id")
        if not did:
            continue
        entry = by_doc.setdefault(
            did, {"doc_id": did, "doc_name": m.get("doc_name", "(unnamed)"), "num_chunks": 0}
        )
        entry["num_chunks"] += 1
    return sorted(by_doc.values(), key=lambda d: d["doc_name"].lower())


def delete_document(doc_id: str) -> int:
    """Delete every chunk belonging to a doc_id. Returns number deleted."""
    coll = get_collection()
    matching = coll.get(where={"doc_id": doc_id})
    ids: Iterable[str] = matching.get("ids") or []
    ids = list(ids)
    if ids:
        coll.delete(ids=ids)
    return len(ids)
