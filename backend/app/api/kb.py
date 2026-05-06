"""
Knowledge-base endpoints — upload, list, delete.

Upload accepts one or more files in a single multipart request. Per-file
ingestion errors don't abort the batch — each file gets its own success or
error entry in the response, so the UI can show partial results.
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import settings
from app.kb.ingestion import delete_document, ingest_file, list_documents


router = APIRouter(prefix="/api/kb", tags=["knowledge-base"])
log = logging.getLogger(__name__)

ALLOWED_SUFFIXES = {".pdf", ".txt", ".md"}
MAX_BYTES = 10 * 1024 * 1024  # 10 MB per file — generous for a demo


async def _process_one(file: UploadFile) -> dict:
    """Validate, save to disk, and ingest a single uploaded file."""
    if not file.filename:
        raise ValueError("Missing filename.")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise ValueError(
            f"Unsupported file type {suffix}. Allowed: {sorted(ALLOWED_SUFFIXES)}"
        )

    dest = settings.uploads_path / file.filename
    try:
        with dest.open("wb") as out:
            shutil.copyfileobj(file.file, out, length=1024 * 1024)
    finally:
        await file.close()

    if dest.stat().st_size > MAX_BYTES:
        dest.unlink(missing_ok=True)
        raise ValueError(f"File too large (>{MAX_BYTES // (1024 * 1024)} MB).")

    return ingest_file(dest, doc_name=file.filename)


@router.post("/upload")
async def upload_documents(files: list[UploadFile] = File(...)):
    """
    Accept one OR many .pdf/.txt/.md files and ingest each into the KB.

    Response shape:
        {
          "results": [ {doc_id, doc_name, num_chunks, char_count}, ... ],
          "errors":  [ {filename, error}, ... ]
        }
    """
    if not files:
        raise HTTPException(400, "No files provided.")

    results: list[dict] = []
    errors: list[dict] = []

    for file in files:
        fname = file.filename or "(unnamed)"
        try:
            result = await _process_one(file)
            log.info("Ingested %s -> %d chunks", fname, result["num_chunks"])
            results.append(result)
        except ValueError as e:
            # Validation problems we want to surface verbatim.
            log.warning("Rejected %s: %s", fname, e)
            errors.append({"filename": fname, "error": str(e)})
        except Exception as e:
            # Unexpected — log full trace, return a sanitized message.
            log.exception("Ingestion failed for %s", fname)
            errors.append({"filename": fname, "error": f"Ingestion failed: {e}"})

    return {"results": results, "errors": errors}


@router.get("/documents")
def get_documents() -> list[dict]:
    return list_documents()


@router.delete("/documents/{doc_id}")
def remove_document(doc_id: str) -> dict:
    deleted = delete_document(doc_id)
    if deleted == 0:
        raise HTTPException(404, "Document not found.")
    return {"doc_id": doc_id, "deleted_chunks": deleted}
