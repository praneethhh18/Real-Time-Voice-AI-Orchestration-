import type { RagSource } from "../lib/api";

/**
 * "RAG sources used" panel.
 *
 * For each user turn, the agent retrieves top-K chunks from the KB and
 * publishes them on the room data channel. We render them here so a
 * reviewer can SEE that RAG actually happened — which is the most
 * important demo signal for this task.
 */
export function RagSources({
  query,
  sources,
}: {
  query: string;
  sources: RagSource[];
}) {
  return (
    <div className="card h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-semibold">RAG Sources</h2>
        <span className="text-xs text-slate-400">
          {sources.length} chunk{sources.length === 1 ? "" : "s"}
        </span>
      </div>

      {query && (
        <div className="mb-3 text-xs">
          <div className="text-slate-400 mb-1">Last query</div>
          <div className="bg-bg border border-border rounded-md px-2 py-1 italic">
            “{query}”
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto space-y-2 pr-1 min-h-[400px]">
        {sources.length === 0 && (
          <p className="text-sm text-slate-400">
            Ask a question during a call. The chunks the agent retrieved from
            your documents will appear here.
          </p>
        )}
        {sources.map((s, i) => (
          <div
            key={`${s.doc_id}-${s.chunk_index}-${i}`}
            className="bg-bg border border-border rounded-md px-3 py-2"
          >
            <div className="flex items-center justify-between gap-2 mb-1">
              <span className="text-xs font-medium truncate">{s.doc_name}</span>
              <span className="text-[10px] text-slate-400 shrink-0">
                chunk #{s.chunk_index}
              </span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed line-clamp-6 whitespace-pre-wrap">
              {s.text}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
