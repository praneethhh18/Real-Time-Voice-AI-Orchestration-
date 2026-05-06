"""
LiveKit access-token endpoint.

The frontend calls this to get a short-lived JWT it uses to join a room.
We also return the LiveKit websocket URL so the frontend doesn't have to
hardcode it.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter
from livekit import api
from pydantic import BaseModel

from app.config import settings


router = APIRouter(prefix="/api", tags=["livekit"])


class TokenRequest(BaseModel):
    # Optional overrides — sane defaults if the caller omits them.
    room_name: str | None = None
    participant_name: str | None = None


class TokenResponse(BaseModel):
    token: str
    url: str
    room: str
    identity: str


@router.post("/token", response_model=TokenResponse)
def create_token(req: TokenRequest) -> TokenResponse:
    room = req.room_name or f"voice-room-{uuid.uuid4().hex[:8]}"
    identity = req.participant_name or f"user-{uuid.uuid4().hex[:6]}"

    grants = api.VideoGrants(
        room=room,
        room_join=True,
        can_publish=True,
        can_subscribe=True,
        can_publish_data=True,
    )

    token = (
        api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
        .with_identity(identity)
        .with_name(identity)
        .with_grants(grants)
        .to_jwt()
    )

    return TokenResponse(
        token=token, url=settings.LIVEKIT_URL, room=room, identity=identity
    )
