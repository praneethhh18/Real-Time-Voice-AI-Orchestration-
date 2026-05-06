"""
Tiny JSON-file-backed shared state.

Currently holds only the editable system prompt. The FastAPI server writes to
it (when the user edits the prompt in the UI); the LiveKit agent reads it on
each new session so prompt changes take effect immediately on the next call.

A file is plenty for a demo — single-machine, single-user. For multi-user
production we'd swap this out for Redis or Postgres.
"""
from __future__ import annotations

import json
import threading
from typing import Any

from app.config import settings


DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful, friendly voice assistant.\n"
    "Keep answers short and conversational — usually 1-3 sentences — since "
    "the user is hearing them spoken aloud.\n"
    "If the user's question is covered by the provided knowledge base context, "
    "answer using ONLY that context and mention briefly which document you used. "
    "If the context is not relevant or empty, answer from your own general knowledge "
    "and say so honestly.\n"
    "Avoid markdown, bullet points, code, or special characters — the response "
    "will be spoken by a text-to-speech engine."
)

# Curated list of Deepgram Aura voices we expose in the UI. Each has a model
# id (passed to deepgram.TTS) and a friendly label shown in the dropdown.
# Mix of male/female and tones so reviewers see we thought about UX.
AVAILABLE_VOICES: list[dict[str, str]] = [
    {"id": "aura-asteria-en", "label": "Asteria · friendly female (default)"},
    {"id": "aura-luna-en",    "label": "Luna · polite mature female"},
    {"id": "aura-stella-en",  "label": "Stella · warm expressive female"},
    {"id": "aura-athena-en",  "label": "Athena · authoritative female"},
    {"id": "aura-orion-en",   "label": "Orion · confident male"},
    {"id": "aura-arcas-en",   "label": "Arcas · natural conversational male"},
    {"id": "aura-perseus-en", "label": "Perseus · energetic male"},
    {"id": "aura-angus-en",   "label": "Angus · male, Irish accent"},
]
DEFAULT_VOICE = "aura-asteria-en"
_VOICE_IDS = {v["id"] for v in AVAILABLE_VOICES}


_lock = threading.Lock()


def _read() -> dict[str, Any]:
    f = settings.state_file
    if not f.exists():
        return {}
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _write(state: dict[str, Any]) -> None:
    settings.state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")


def get_system_prompt() -> str:
    with _lock:
        return _read().get("system_prompt", DEFAULT_SYSTEM_PROMPT)


def set_system_prompt(prompt: str) -> str:
    prompt = prompt.strip() or DEFAULT_SYSTEM_PROMPT
    with _lock:
        state = _read()
        state["system_prompt"] = prompt
        _write(state)
    return prompt


def get_voice() -> str:
    with _lock:
        v = _read().get("voice", DEFAULT_VOICE)
    # Defensive: if state.json has been hand-edited to an unknown voice
    # (e.g. someone bumped the AVAILABLE_VOICES list), fall back to default
    # so the agent doesn't crash trying to use a nonexistent Deepgram model.
    return v if v in _VOICE_IDS else DEFAULT_VOICE


def set_voice(voice_id: str) -> str:
    if voice_id not in _VOICE_IDS:
        raise ValueError(f"Unknown voice id: {voice_id!r}")
    with _lock:
        state = _read()
        state["voice"] = voice_id
        _write(state)
    return voice_id
