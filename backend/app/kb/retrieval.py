"""
Retrieval: given a user query, return the top-K most relevant chunks.

Used by the LiveKit voice agent on every user turn to inject grounded
context into the LLM call (RAG).
"""
from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.kb.store import get_collection


@dataclass
class RetrievedChunk:
    """One result from the vector store, in a JSON-friendly shape."""
    text: str
    doc_name: str
    doc_id: str
    chunk_index: int
    score: float  # cosine similarity in [0,1]; higher = more relevant

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "doc_name": self.doc_name,
            "doc_id": self.doc_id,
            "chunk_index": self.chunk_index,
            "score": round(self.score, 4),
        }


def retrieve(query: str, k: int | None = None) -> list[RetrievedChunk]:
    """Return the top-K most relevant chunks for `query`. Empty list if KB empty."""
    if not query or not query.strip():
        return []

    k = k or settings.RAG_TOP_K
    coll = get_collection()
    if coll.count() == 0:
        return []

    res = coll.query(
        query_texts=[query],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )

    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]

    out: list[RetrievedChunk] = []
    for text, meta, dist in zip(docs, metas, dists):
        meta = meta or {}
        # Chroma cosine "distance" is (1 - cosine_similarity); flip back so a
        # higher score = more relevant, which is what humans expect in a UI.
        score = max(0.0, 1.0 - float(dist))
        out.append(
            RetrievedChunk(
                text=text,
                doc_name=meta.get("doc_name", "(unknown)"),
                doc_id=meta.get("doc_id", ""),
                chunk_index=int(meta.get("chunk_index", 0)),
                score=score,
            )
        )
    return out
