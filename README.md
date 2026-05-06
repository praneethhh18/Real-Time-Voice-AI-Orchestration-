# Real-Time Voice AI Orchestrator

End-to-end real-time voice agent. The user talks to the agent over WebRTC
(LiveKit). The agent answers using an editable system prompt and **RAG over
documents the user has uploaded** during the call.

> Round 1 task submission. Built with separation of concerns in mind: each
> pipeline stage (STT, LLM, TTS, KB) is an isolated component you can swap
> without touching the others.

---

## Quick start (Windows, one click)

1. Make sure `backend\.env` exists and is filled in (copy from `backend\.env.example`).
2. **Double-click `start.bat`** in this folder. (Or, in PowerShell: `.\start.ps1`)

The launcher will:
- create the Python virtualenv (first run only)
- install Python + Node dependencies (first run only)
- open three terminal windows: backend API, voice agent, frontend
- open `http://localhost:5173` in your browser

To stop: close the three windows, or run `.\stop.ps1`.

For non-Windows / Docker / manual steps, see [Setup](#setup) below.

---

## Architecture

```
┌───────────────┐    WebRTC    ┌───────────────┐    WebRTC    ┌──────────────────┐
│   Browser     │ ───────────► │ LiveKit Cloud │ ◄─────────── │  Voice Agent     │
│  React + LK   │    audio     │   (SFU)       │    audio     │  (Python worker) │
│  components   │              └───────────────┘              │                  │
└──────┬────────┘                                             │  Silero VAD      │
       │ HTTP                                                 │  Deepgram STT    │
       │  /api/token                                          │  ── RAG hook ──  │──┐
       │  /api/kb/*                                           │  Groq LLM        │  │
       │  /api/prompt                                         │  Deepgram TTS    │  │
       ▼                                                      └────────┬─────────┘  │
┌───────────────┐                                                      │            │
│  FastAPI      │  ◄───── shared volume: data/state.json ──────────────┘            │
│  (backend)    │                                                                   │
└──────┬────────┘                                                                   │
       │                                                                            │
       │  embed + persist           query (top-K)                                   │
       ▼                                                                            │
┌───────────────────────────────────────────────────────────────────────────────────┘
│  ChromaDB (embedded)  ←  sentence-transformers/all-MiniLM-L6-v2
└──────────────────────────────────────────────────────────────────
```

### Pipeline components (each is one module — swappable)

| Stage     | Implementation                       | File                                  |
| --------- | ------------------------------------ | ------------------------------------- |
| Transport | LiveKit Cloud (WebRTC)               | `backend/app/api/token.py` (server)   |
| VAD       | Silero (local)                       | `backend/app/agent/voice_agent.py`    |
| STT       | Deepgram `nova-2` (streaming)        | `backend/app/agent/voice_agent.py`    |
| LLM       | Groq `llama-3.3-70b-versatile` (free)| `backend/app/agent/voice_agent.py`    |
| TTS       | Deepgram Aura (`aura-asteria-en`)    | `backend/app/agent/voice_agent.py`    |
| Embeds    | `sentence-transformers/all-MiniLM-L6-v2` (local) | `backend/app/kb/store.py`         |
| Vector DB | ChromaDB (embedded, persistent)      | `backend/app/kb/store.py`             |
| Ingestion | pypdf + recursive char chunker       | `backend/app/kb/ingestion.py`         |
| Retrieval | Cosine top-K                         | `backend/app/kb/retrieval.py`         |

The **RAG hook** lives in `VoiceAssistant.on_user_turn_completed`
(`backend/app/agent/voice_agent.py`). It runs after STT finalizes a user
turn and before the LLM is called: retrieve top-K chunks → inject them as a
system message in the chat context → also publish them to the frontend over
the room data channel for the "RAG sources used" panel.

---

## Setup

### 1. Prerequisites

- Python 3.10+
- Node.js 18+
- (Optional) Docker + Docker Compose
- A LiveKit Cloud project (free tier works) — https://cloud.livekit.io
- A Deepgram API key (free credit) — https://console.deepgram.com
- A Groq API key (free) — https://console.groq.com

### 2. Clone & configure env

```bash
git clone https://github.com/praneethhh18/Real-Time-Voice-AI-Orchestration-.git
cd Real-Time-Voice-AI-Orchestration-
cp backend/.env.example backend/.env
# then open backend/.env and fill in:
#   LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET
#   DEEPGRAM_API_KEY
#   GROQ_API_KEY
```

### 3a. Run with Docker (recommended)

```bash
docker compose up --build
```

Open http://localhost:5173.

### 3b. Run locally without Docker

You need three terminals.

**Terminal 1 — backend (FastAPI):**

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — voice agent worker:**

```bash
cd backend
# (same venv as terminal 1)
.\.venv\Scripts\Activate.ps1   # Windows
# source .venv/bin/activate    # macOS/Linux
python -m app.agent.voice_agent dev
```

> The first time the agent starts it will download the
> `all-MiniLM-L6-v2` embedding model (~80 MB) and the Silero VAD model.
> Subsequent runs are fast.

**Terminal 3 — frontend:**

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

---

## Environment variables

| Variable             | Required | Default                          | Notes                                       |
| -------------------- | -------- | -------------------------------- | ------------------------------------------- |
| `LIVEKIT_URL`        | yes      | —                                | `wss://<project>.livekit.cloud`             |
| `LIVEKIT_API_KEY`    | yes      | —                                | from LiveKit project settings               |
| `LIVEKIT_API_SECRET` | yes      | —                                | from LiveKit project settings               |
| `DEEPGRAM_API_KEY`   | yes      | —                                | used for both STT and TTS                   |
| `GROQ_API_KEY`       | yes      | —                                | OpenAI-compatible Groq endpoint             |
| `LLM_MODEL`          | no       | `llama-3.3-70b-versatile`        | any Groq model                              |
| `EMBEDDING_MODEL`    | no       | `all-MiniLM-L6-v2`               | any sentence-transformers model             |
| `STT_MODEL`          | no       | `nova-2`                         | Deepgram STT model                          |
| `TTS_MODEL`          | no       | `aura-asteria-en`                | Deepgram Aura voice                         |
| `RAG_TOP_K`          | no       | `4`                              | chunks retrieved per user turn              |
| `DATA_DIR`           | no       | `./data`                         | where `chroma/`, `uploads/`, state.json go  |

---

## Project layout

```
Task1 Voice/
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   │   └── voice_agent.py     # LiveKit worker: STT/LLM/TTS + RAG hook
│   │   ├── api/
│   │   │   ├── kb.py              # /api/kb/* endpoints
│   │   │   ├── prompt.py          # /api/prompt endpoints
│   │   │   ├── token.py           # /api/token endpoint
│   │   │   └── voice.py           # /api/voice (TTS voice picker)
│   │   ├── kb/
│   │   │   ├── ingestion.py       # extract -> chunk -> embed -> store
│   │   │   ├── retrieval.py       # top-K cosine search
│   │   │   └── store.py           # ChromaDB singleton + embedder
│   │   ├── config.py              # env loader (pydantic-settings)
│   │   ├── main.py                # FastAPI app
│   │   └── state.py               # shared state.json (system prompt)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── KBManager.tsx       # upload + list + delete docs
│   │   │   ├── PromptEditor.tsx    # editable system prompt
│   │   │   ├── RagSources.tsx      # "sources used" panel
│   │   │   ├── RoomEventBridge.tsx # LiveKit events -> React state
│   │   │   ├── Transcript.tsx      # live partial+final transcript
│   │   │   ├── VoiceCall.tsx       # call controls + visualizer
│   │   │   └── VoicePicker.tsx     # TTS voice dropdown
│   │   ├── lib/api.ts              # typed fetch wrappers
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
├── sample-documents/             # demo files to upload during the demo
├── start.bat                     # Windows: double-click to launch everything
├── start.ps1                     # PowerShell launcher
├── stop.ps1                      # cleanly stop all 3 services
├── docker-compose.yml
└── README.md
```

---

## How it all fits together (one full turn)

1. User clicks **Start Call** → frontend `POST /api/token` → LiveKit JWT.
2. Browser joins the LiveKit room (publishing mic, subscribing audio).
3. The voice-agent worker (already running) is dispatched into the room and
   joins automatically.
4. User speaks. Deepgram emits **partial** STT segments → LiveKit
   `TranscriptionReceived` events → transcript panel updates in real time.
5. When the turn finalizes, `VoiceAssistant.on_user_turn_completed` runs:
   - calls `retrieve(query, k=4)` → top-K chunks from ChromaDB,
   - inserts them as a system message in the LLM chat context,
   - publishes them on the room data channel (topic `rag`) → the **RAG
     Sources** panel updates in the UI.
6. Groq LLM streams a reply → Deepgram TTS streams audio frames → the
   agent publishes them to the room → browser plays them.
7. The agent's reply also comes back as a transcription event, so the
   transcript shows both sides of the conversation.

---

## Known limitations / tradeoffs

- **Single-user, single-machine demo.** The system prompt is stored in a
  JSON file shared between the API and the agent over a bind-mounted
  volume. For multi-user production, swap `state.py` for Redis/Postgres and
  pass per-room metadata via the LiveKit token instead.
- **System prompt updates apply to the next call**, not mid-call. The
  agent reads the prompt once at session start. The UI disables the editor
  while a call is in progress to make this contract obvious.
- **No re-ranking.** Pure cosine top-K. For more complex KBs, adding a
  cross-encoder re-ranker on the top-20 → top-4 would improve quality.
- **Chunking is character-based.** Token-aware chunking would be slightly
  better but would require an extra dependency.
- **No auth.** CORS is open and the token endpoint is unauthenticated. Fine
  for a demo, not for production.
- **Cold-start latency on first run** (~10s) while sentence-transformers
  downloads the embedding model. Subsequent starts are sub-second.
- **Free-tier rate limits** apply on Groq and Deepgram. For a demo this is
  not an issue.

---

## Operational notes (the bonus criterion)

- All services log structured-ish lines with a level prefix; `grep` works.
- The agent logs every retrieval (`RAG: query=… retrieved N chunks (top score=…)`)
  which doubles as a metrics hook — pipe it to Loki/Grafana to graph
  retrieval health.
- Dockerized: `docker compose up --build` brings up backend + agent +
  frontend with one command.
- Healthcheck on `backend:/health` so `agent` only starts after the API
  is reachable (matters because the agent reads `state.json` from the
  shared volume).
