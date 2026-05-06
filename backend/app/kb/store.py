"""
Vector store wrapper around ChromaDB.

Why ChromaDB: it's an embedded vector DB - no server, no auth, just a folder
on disk. Perfect for a single-machine demo. Persists across restarts.

Embedding model: `sentence-transformers/all-MiniLM-L6-v2` runs locally on CPU.
384-dim vectors, ~80MB download on first run, no API quota to worry about.

Caching strategy:
  - The embedding function and the PersistentClient are cached at module
    level (loading them is slow: ~2-5s for the embedder).
  - The Collection reference is NOT cached: we re-fetch it on every call.
    Collection lookup is cheap, and re-fetching avoids stale-view bugs when
    a different process (e.g. the agent worker) writes to the same Chroma
    directory between calls.
"""
from __future__ import annotations

import threading
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions

from app.config import settings


# Must be 3-63 chars, alnum + underscore/hyphen — Chroma rejects "kb" as too short.
_KB_COLLECTION = "knowledge_base"

_lock = threading.Lock()
_client: Any = None
_embedder: Any = None


def _ensure_client_and_embedder() -> None:
    """Lazily create the heavy singletons (client + embedder)."""
    global _client, _embedder
    if _client is not None and _embedder is not None:
        return

    with _lock:
        if _embedder is None:
            _embedder = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=settings.EMBEDDING_MODEL
            )
        if _client is None:
            _client = chromadb.PersistentClient(
                path=str(settings.chroma_path),
                settings=ChromaSettings(anonymized_telemetry=False),
            )


def get_collection():
    """
    Return a fresh handle to our KB collection.

    We deliberately do NOT cache the Collection object. ChromaDB's
    persistent client is fine to share across calls, but holding a stale
    Collection reference between writes from another process (or after a
    uvicorn reload) can return empty results from `get()`. Re-fetching is
    cheap and removes that footgun entirely.
    """
    _ensure_client_and_embedder()
    return _client.get_or_create_collection(
        name=_KB_COLLECTION,
        embedding_function=_embedder,
        metadata={"hnsw:space": "cosine"},
    )
