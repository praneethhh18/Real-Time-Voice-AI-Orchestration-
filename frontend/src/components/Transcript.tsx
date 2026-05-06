import { useEffect, useRef } from "react";

export type TranscriptEntry = {
  id: string;
  role: "user" | "agent";
  text: string;
  final: boolean;
};

/**
 * Live transcript view: shows both user (STT) and agent (TTS) segments.
 * Partial segments render in lighter color until LiveKit marks them final.
 *
 * Auto-scrolls to the latest entry so it always feels "live".
 */
export function Transcript({ entries }: { entries: TranscriptEntry[] }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    ref.current?.scrollTo({ top: ref.current.scrollHeight, behavior: "smooth" });
  }, [entries]);

  return (
    <div className="card h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-semibold">Live Transcript</h2>
        <span className="text-xs text-slate-400">
          {entries.length} segment{entries.length === 1 ? "" : "s"}
        </span>
      </div>

      <div
        ref={ref}
        className="flex-1 overflow-y-auto space-y-2 pr-1 min-h-[400px]"
      >
        {entries.length === 0 && (
          <p className="text-sm text-slate-400">
            Start a call and speak. Partial and final transcripts appear here in real time.
          </p>
        )}
        {entries.map((e) => (
          <div
            key={e.id}
            className={`flex gap-3 ${e.role === "user" ? "" : "flex-row-reverse"}`}
          >
            <div
              className={`max-w-[85%] rounded-lg px-3 py-2 text-sm leading-snug ${
                e.role === "user"
                  ? "bg-bg border border-border"
                  : "bg-accent/15 border border-accent/30"
              } ${e.final ? "" : "opacity-60 italic"}`}
            >
              <div className="text-[10px] uppercase tracking-wide mb-0.5 text-slate-400">
                {e.role}
                {!e.final && " · partial"}
              </div>
              {e.text}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
