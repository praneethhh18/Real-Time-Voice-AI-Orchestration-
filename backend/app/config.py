"""
Central configuration loader.

All env vars are read once here and exposed via a single `settings` object
so that other modules don't have to touch `os.environ` directly. This keeps
configuration testable and lets us swap providers in one place.
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # LiveKit (voice transport over WebRTC)
    LIVEKIT_URL: str
    LIVEKIT_API_KEY: str
    LIVEKIT_API_SECRET: str

    # Deepgram (handles both speech-to-text and text-to-speech)
    DEEPGRAM_API_KEY: str

    # Groq (free, low-latency LLM inference; OpenAI-compatible API)
    GROQ_API_KEY: str

    # Model + retrieval tuning
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    STT_MODEL: str = "nova-2"
    TTS_MODEL: str = "aura-asteria-en"
    RAG_TOP_K: int = 4

    # Where ChromaDB + uploaded files + state.json live on disk
    DATA_DIR: str = "./data"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def data_path(self) -> Path:
        p = Path(self.DATA_DIR).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def uploads_path(self) -> Path:
        p = self.data_path / "uploads"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def chroma_path(self) -> Path:
        p = self.data_path / "chroma"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def state_file(self) -> Path:
        # Shared mutable state (currently just the system prompt) that the
        # FastAPI server writes and the LiveKit agent reads on each session.
        return self.data_path / "state.json"


settings = Settings()
