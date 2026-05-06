import { useEffect, useState } from "react";
import { LiveKitRoom, RoomAudioRenderer } from "@livekit/components-react";
import { fetchToken } from "./lib/api";
import type { TokenResponse, RagSource } from "./lib/api";
import { VoiceCall } from "./components/VoiceCall";
import { PromptEditor } from "./components/PromptEditor";
import { VoicePicker } from "./components/VoicePicker";
import { KBManager } from "./components/KBManager";
import { Transcript, type TranscriptEntry } from "./components/Transcript";
import { RagSources } from "./components/RagSources";
import { RoomEventBridge } from "./components/RoomEventBridge";

/**
 * Top-level app.
 *
 * Layout: a 3-column grid on desktop. Left = controls (call + KB + prompt),
 * middle = live transcript, right = RAG sources used. The whole right two
 * columns become "live" once the call starts.
 *
 * State that's shared across components (transcript entries, RAG sources)
 * lives here and is passed down. Keeps things explicit and easy to trace.
 */
export default function App() {
  const [conn, setConn] = useState<TokenResponse | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Shared live state coming back from the LiveKit room.
  const [entries, setEntries] = useState<TranscriptEntry[]>([]);
  const [sources, setSources] = useState<RagSource[]>([]);
  const [lastQuery, setLastQuery] = useState<string>("");

  async function startCall() {
    setError(null);
    setConnecting(true);
    try {
      const token = await fetchToken();
      // Reset call-scoped state when starting a new call.
      setEntries([]);
      setSources([]);
      setLastQuery("");
      setConn(token);
    } catch (e: any) {
      setError(e.message ?? "Failed to start call");
    } finally {
      setConnecting(false);
    }
  }

  function endCall() {
    setConn(null);
  }

  // If the room disconnects on its own (network drop, etc.), reflect that.
  useEffect(() => {
    if (!conn) return;
  }, [conn]);

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-border px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold leading-tight">Voice AI Orchestrator</h1>
          <p className="text-xs text-slate-400">LiveKit · Deepgram · Groq · ChromaDB RAG</p>
        </div>
        <span
          className={`text-xs px-2 py-1 rounded-md border ${
            conn
              ? "border-green-500/40 text-green-300 bg-green-500/10"
              : "border-border text-slate-400"
          }`}
        >
          {conn ? `Connected · ${conn.room}` : "Idle"}
        </span>
      </header>

      <main className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-4 p-4">
        {/* Left column: controls */}
        <section className="lg:col-span-4 space-y-4">
          <VoiceCall
            connected={!!conn}
            connecting={connecting}
            onStart={startCall}
            onEnd={endCall}
          />
          <PromptEditor disabled={!!conn} />
          <VoicePicker disabled={!!conn} />
          <KBManager />
        </section>

        {/* Middle: transcript */}
        <section className="lg:col-span-5">
          <Transcript entries={entries} />
        </section>

        {/* Right: RAG sources */}
        <section className="lg:col-span-3">
          <RagSources query={lastQuery} sources={sources} />
        </section>
      </main>

      {error && (
        <div className="fixed bottom-4 right-4 bg-red-500/90 text-white px-4 py-2 rounded-lg shadow-lg">
          {error}
        </div>
      )}

      {/* The LiveKitRoom only mounts while we have a token. All components
          that need access to the room (audio renderer, transcript bridge,
          data-channel listener) live as its children. */}
      {conn && (
        <LiveKitRoom
          token={conn.token}
          serverUrl={conn.url}
          connect
          audio
          video={false}
          onDisconnected={endCall}
          onError={(e) => setError(e.message)}
        >
          {/* Plays the agent's TTS audio through the speakers. */}
          <RoomAudioRenderer />

          {/* Bridges LiveKit events -> React state above. */}
          <RoomEventBridge
            onTranscript={(e) =>
              setEntries((prev) => mergeEntry(prev, e))
            }
            onRagSources={(query, srcs) => {
              setLastQuery(query);
              setSources(srcs);
            }}
          />
        </LiveKitRoom>
      )}
    </div>
  );
}

// Merge a partial transcript update into the list: if an entry with the same
// id exists, replace it; otherwise append. This lets us update partials in
// place and finalize them when STT marks them final.
function mergeEntry(prev: TranscriptEntry[], next: TranscriptEntry): TranscriptEntry[] {
  const idx = prev.findIndex((e) => e.id === next.id);
  if (idx === -1) return [...prev, next];
  const copy = prev.slice();
  copy[idx] = next;
  return copy;
}
