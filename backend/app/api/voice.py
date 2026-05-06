"""TTS voice picker endpoints. Same shape as /api/prompt."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.state import AVAILABLE_VOICES, get_voice, set_voice


router = APIRouter(prefix="/api/voice", tags=["voice"])


class VoiceState(BaseModel):
    current: str
    available: list[dict]   # [{id, label}, ...]


class VoiceUpdate(BaseModel):
    voice_id: str


@router.get("", response_model=VoiceState)
def read_voice() -> VoiceState:
    return VoiceState(current=get_voice(), available=AVAILABLE_VOICES)


@router.put("", response_model=VoiceState)
def update_voice(req: VoiceUpdate) -> VoiceState:
    try:
        set_voice(req.voice_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return VoiceState(current=get_voice(), available=AVAILABLE_VOICES)
