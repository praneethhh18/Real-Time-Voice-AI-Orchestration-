import {
  useLocalParticipant,
  BarVisualizer,
  useVoiceAssistant,
} from "@livekit/components-react";

/**
 * Call control card (always visible in the left column).
 *
 * When idle: shows a Start Call button.
 * When connected: shows a placeholder note — the actual mic toggle and
 * agent visualizer live inside <LiveKitRoom> via `InRoomCallControls`
 * (rendered from RoomEventBridge), because the LiveKit hooks they use
 * require a Room provider above them.
 */
export function VoiceCall({
  connected,
  connecting,
  onStart,
  onEnd,
}: {
  connected: boolean;
  connecting: boolean;
  onStart: () => void;
  onEnd: () => void;
}) {
  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-semibold">Voice Call</h2>
        <span className="text-xs text-slate-400">WebRTC · LiveKit</span>
      </div>

      {!connected ? (
        <button
          className="btn-primary w-full"
          onClick={onStart}
          disabled={connecting}
        >
          {connecting ? "Connecting…" : "Start Call"}
        </button>
      ) : (
        <div className="space-y-3">
          <div className="rounded-lg border border-border bg-bg/60 p-3 text-xs text-slate-400">
            Mic and visualizer are active at the bottom of the screen. Speak naturally.
          </div>
          <button className="btn-ghost w-full" onClick={onEnd}>
            End Call
          </button>
        </div>
      )}
    </div>
  );
}

/**
 * Floating call-controls bar mounted inside <LiveKitRoom>.
 *
 * Pill-shaped, centered at the bottom, glass-blurred. The accent dot on
 * the left changes colour based on the agent's state so a viewer can tell
 * at a glance whether the agent is listening, thinking, or speaking —
 * exactly the kind of polish that reads well on a demo video.
 */

// Map LiveKit's voice-assistant state to a small visual style payload.
function stateStyle(state: string) {
  switch (state) {
    case "connecting":
    case "initializing":
      return { color: "bg-amber-400", ring: "ring-amber-400/30", label: "Connecting", pulse: true };
    case "listening":
      return { color: "bg-emerald-400", ring: "ring-emerald-400/30", label: "Listening", pulse: false };
    case "thinking":
      return { color: "bg-violet-400", ring: "ring-violet-400/30", label: "Thinking", pulse: true };
    case "speaking":
      return { color: "bg-accent2", ring: "ring-accent2/30", label: "Speaking", pulse: false };
    default:
      return { color: "bg-slate-400", ring: "ring-slate-400/30", label: state || "Idle", pulse: false };
  }
}

export function InRoomCallControls() {
  const { localParticipant, isMicrophoneEnabled } = useLocalParticipant();
  const { state, audioTrack } = useVoiceAssistant();
  const s = stateStyle(state);

  return (
    <div
      className="fixed bottom-6 left-1/2 -translate-x-1/2 z-20
                 flex items-center gap-2.5 px-3 py-1.5
                 bg-panel/80 backdrop-blur-md
                 border border-border rounded-full shadow-xl
                 w-[min(88vw,380px)]"
    >
      {/* state indicator dot — pulses on active states */}
      <span
        className={`relative inline-flex items-center justify-center w-2.5 h-2.5 ml-1 shrink-0`}
        title={s.label}
      >
        <span
          className={`absolute inline-flex w-full h-full rounded-full ${s.color} ${
            s.pulse ? "animate-ping opacity-75" : "opacity-0"
          }`}
        />
        <span className={`relative inline-flex w-2.5 h-2.5 rounded-full ${s.color} ring-4 ${s.ring}`} />
      </span>

      {/* state label, fixed-ish width so the visualizer doesn't jump */}
      <span className="text-[11px] font-medium text-slate-300 min-w-[58px]">{s.label}</span>

      {/* live audio visualizer of the agent's voice */}
      <div className="flex-1 h-7 flex items-center">
        <BarVisualizer
          state={state}
          trackRef={audioTrack}
          barCount={18}
          options={{ minHeight: 2 }}
        />
      </div>

      {/* mic toggle — circular icon button, not a wide labelled one */}
      <button
        onClick={() => localParticipant.setMicrophoneEnabled(!isMicrophoneEnabled)}
        title={isMicrophoneEnabled ? "Mute mic" : "Unmute mic"}
        aria-label={isMicrophoneEnabled ? "Mute mic" : "Unmute mic"}
        className={`shrink-0 w-9 h-9 rounded-full flex items-center justify-center transition-colors ${
          isMicrophoneEnabled
            ? "bg-accent text-white hover:bg-accent/90"
            : "bg-red-500/20 text-red-300 border border-red-500/40 hover:bg-red-500/30"
        }`}
      >
        {isMicrophoneEnabled ? <MicIcon /> : <MicOffIcon />}
      </button>
    </div>
  );
}

function MicIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="2" width="6" height="12" rx="3" />
      <path d="M19 10a7 7 0 0 1-14 0" />
      <line x1="12" y1="19" x2="12" y2="22" />
    </svg>
  );
}

function MicOffIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="2" y1="2" x2="22" y2="22" />
      <path d="M9 9v3a3 3 0 0 0 5.12 2.12" />
      <path d="M15 9.34V5a3 3 0 0 0-5.94-.6" />
      <path d="M19 10a7 7 0 0 1-.11 1.23" />
      <path d="M5 10a7 7 0 0 0 12 5" />
      <line x1="12" y1="19" x2="12" y2="22" />
    </svg>
  );
}
