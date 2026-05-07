"""
LiveKit voice agent worker.

This is a **separate process** from the FastAPI server. It registers with
LiveKit Cloud and is dispatched into rooms automatically. Inside a room it
runs the full real-time pipeline:

    mic audio (WebRTC)
        -> Silero VAD (detects when the user is speaking)
        -> Deepgram STT  (streaming speech-to-text, partial + final)
        -> [RAG hook]    (we override on_user_turn_completed to inject KB context)
        -> Groq LLM      (Llama 3.3 70B via OpenAI-compatible API)
        -> Deepgram TTS  (streaming text-to-speech)
        -> speaker (WebRTC)

We also forward the retrieved KB chunks to the frontend over the room's
data channel so the UI can show a "RAG sources used" panel.

Run with:    python -m app.agent.voice_agent dev
Or in prod:  python -m app.agent.voice_agent start
"""
from __future__ import annotations

# Load .env into os.environ BEFORE importing livekit.agents — its CLI reads
# LIVEKIT_URL/KEY/SECRET directly from the process environment, and our
# pydantic Settings object only populates itself, not os.environ.
# We resolve the .env path explicitly (relative to this file) so it doesn't
# matter what working directory the agent is launched from.
from pathlib import Path
from dotenv import load_dotenv
_env_file = Path(__file__).resolve().parents[2] / ".env"   # backend/.env
load_dotenv(_env_file, override=False)

import asyncio
import json
import logging
from typing import Any

from livekit.agents import (
    Agent,
    AgentSession,
    ChatContext,
    ChatMessage,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
)
from livekit.plugins import deepgram, openai, silero

from app.config import settings
from app.kb.retrieval import retrieve
from app.kb.store import get_collection
from app.state import get_system_prompt, get_voice


log = logging.getLogger("voice-agent")


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class VoiceAssistant(Agent):
    """
    Custom Agent with a RAG hook.

    `on_user_turn_completed` runs after the STT has produced a final
    transcript for the user's turn but BEFORE the LLM is called. That's the
    perfect spot to retrieve relevant chunks and inject them as a system
    message so the LLM grounds its reply in our docs.
    """

    def __init__(self, instructions: str, room: Any) -> None:
        super().__init__(instructions=instructions)
        self._room = room

    async def on_user_turn_completed(
        self, turn_ctx: ChatContext, new_message: ChatMessage
    ) -> None:
        user_text = (new_message.text_content or "").strip()
        if not user_text:
            return

        # 1) Retrieve top-K chunks from the vector store.
        try:
            chunks = retrieve(user_text, k=settings.RAG_TOP_K)
        except Exception:
            log.exception("RAG retrieval failed; continuing without context")
            chunks = []

        # 2) If we got useful chunks, splice them into the chat context for
        #    this turn only. The agent framework keeps these messages out of
        #    the persistent history once the turn is finished.
        if chunks:
            joined = "\n\n---\n\n".join(
                f"[Source: {c.doc_name}]\n{c.text}" for c in chunks
            )
            turn_ctx.add_message(
                role="system",
                content=(
                    "Knowledge base context (use if relevant; ignore if not):\n"
                    f"{joined}"
                ),
            )
            log.info(
                "RAG: query=%r | retrieved %d chunks (top score=%.3f)",
                user_text[:80],
                len(chunks),
                chunks[0].score,
            )

        # 3) Forward the retrieval result to the frontend so the UI can show
        #    a "RAG sources used" panel. Fire-and-forget — don't block the LLM.
        asyncio.create_task(self._publish_sources(user_text, chunks))

    async def _publish_sources(self, query: str, chunks) -> None:
        try:
            payload = {
                "type": "rag_sources",
                "query": query,
                "sources": [c.to_dict() for c in chunks],
            }
            await self._room.local_participant.publish_data(
                json.dumps(payload).encode("utf-8"),
                reliable=True,
                topic="rag",
            )
        except Exception:
            log.exception("Failed to publish RAG sources to frontend")


# ---------------------------------------------------------------------------
# Worker entrypoint
# ---------------------------------------------------------------------------

def prewarm(proc: JobProcess) -> None:
    """
    Run ONCE per agent worker process, before any call is dispatched into it.

    We use this to load the slow stuff up-front so the first user turn isn't
    delayed by ~25 seconds:
      - Silero VAD model
      - sentence-transformers embedding model (~80 MB on first run)
      - ChromaDB collection initialisation

    Without this, all of that happens lazily *during* the first user turn,
    blocking the event loop, and Deepgram even times out the STT websocket
    because no audio reaches it for ~25s.
    """
    log.info("prewarm: loading Silero VAD...")
    proc.userdata["vad"] = silero.VAD.load()

    log.info("prewarm: warming up ChromaDB + embedding model...")
    coll = get_collection()
    # A throwaway query forces sentence-transformers to actually load the
    # model (it's lazy by default — just calling get_collection() doesn't
    # trigger the download/load).
    try:
        coll.query(query_texts=["warmup"], n_results=1)
    except Exception:
        # KB may be empty on first launch; that's fine — model still loaded.
        pass
    log.info("prewarm: done — agent is ready for low-latency calls")


async def entrypoint(ctx: JobContext) -> None:
    """Called by the LiveKit worker once per room the agent joins."""
    await ctx.connect()
    log.info("Agent joined room: %s", ctx.room.name)

    # Read the latest user-edited system prompt + voice at session start.
    # Edits in the UI take effect on the NEXT call, not mid-call.
    system_prompt = get_system_prompt()
    voice_id = get_voice()
    log.info("Session config: voice=%s", voice_id)

    # Prefer the prewarmed VAD instance, but fall back to loading inline if
    # for any reason prewarm didn't run (e.g., the dev-mode watcher reloaded
    # only part of the module). The agent must keep working either way.
    vad = None
    if ctx.proc and ctx.proc.userdata:
        vad = ctx.proc.userdata.get("vad")
    if vad is None:
        log.warning("VAD not prewarmed; loading inline (this call will be ~1s slower)")
        vad = silero.VAD.load()

    session = AgentSession(
        vad=vad,
        stt=deepgram.STT(model=settings.STT_MODEL, api_key=settings.DEEPGRAM_API_KEY),
        # The LLM is OpenAI-compatible; we point base_url at our chosen
        # provider. Defaults to Groq, but if LLM_API_KEY is set in .env we
        # use that + LLM_BASE_URL instead — easy backup if Groq is blocked.
        llm=openai.LLM(
            model=settings.LLM_MODEL,
            api_key=settings.LLM_API_KEY or settings.GROQ_API_KEY,
            base_url=settings.LLM_BASE_URL,
        ),
        tts=deepgram.TTS(model=voice_id, api_key=settings.DEEPGRAM_API_KEY),
    )

    agent = VoiceAssistant(instructions=system_prompt, room=ctx.room)

    await session.start(agent=agent, room=ctx.room)

    # Greet the user as soon as they connect. Without this the agent waits
    # for the first user utterance, which feels broken in a demo.
    await session.generate_reply(
        instructions=(
            "Greet the user warmly in one short sentence and tell them you "
            "can answer questions about any documents they've uploaded."
        )
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
