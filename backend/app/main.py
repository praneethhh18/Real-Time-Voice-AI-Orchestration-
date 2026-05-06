"""
FastAPI entry point.

Wires together the three route groups (token, KB, prompt) and enables CORS
so the React dev server (Vite, port 5173) can talk to it.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import kb, prompt, token, voice


# Structured-ish logging — fine for a demo, easy to grep.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


app = FastAPI(title="Voice AI Orchestrator", version="0.1.0")

# Open CORS for the demo — in production we'd restrict to the frontend origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(token.router)
app.include_router(kb.router)
app.include_router(prompt.router)
app.include_router(voice.router)


@app.get("/health")
def health() -> dict:
    """Liveness probe for Docker / load balancers."""
    return {"status": "ok"}
