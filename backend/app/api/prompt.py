"""System prompt: GET to view, PUT to update. Used by the prompt editor in the UI."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.state import get_system_prompt, set_system_prompt


router = APIRouter(prefix="/api/prompt", tags=["prompt"])


class PromptResponse(BaseModel):
    system_prompt: str


class PromptUpdate(BaseModel):
    system_prompt: str = Field(..., min_length=1, max_length=8000)


@router.get("", response_model=PromptResponse)
def read_prompt() -> PromptResponse:
    return PromptResponse(system_prompt=get_system_prompt())


@router.put("", response_model=PromptResponse)
def update_prompt(req: PromptUpdate) -> PromptResponse:
    saved = set_system_prompt(req.system_prompt)
    return PromptResponse(system_prompt=saved)
