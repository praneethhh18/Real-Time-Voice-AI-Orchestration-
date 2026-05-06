import { useEffect, useRef, useState } from "react";
import {
  deleteDocument,
  listDocuments,
  uploadDocuments,
  type KbDocument,
} from "../lib/api";

/**
 * Knowledge base manager: drag-and-drop or click to upload one or more
 * files, list ingested docs, delete them. Per-file errors are surfaced
 * separately so a single bad file doesn't mask successful uploads.
 */
export function KBManager() {
  const [docs, setDocs] = useState<KbDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [errors, setErrors] = useState<{ filename: string; error: string }[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);

  async function refresh() {
    setLoading(true);
    try {
      setDocs(await listDocuments());
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function onUpload(files: File[]) {
    if (!files.length) return;
    setErrors([]);
    setUploading(true);
    try {
      const res = await uploadDocuments(files);
      if (res.errors?.length) setErrors(res.errors);
      await refresh();
    } catch (e: any) {
      // network/total failure — show as a single synthetic error
      setErrors([{ filename: "(request)", error: e.message ?? "Upload failed" }]);
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function onDelete(doc_id: string) {
    if (!confirm("Delete this document from the knowledge base?")) return;
    await deleteDocument(doc_id);
    await refresh();
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-semibold">Knowledge Base</h2>
        <span className="text-xs text-slate-400">.pdf · .txt · .md</span>
      </div>

      <label
        className={`flex flex-col items-center justify-center text-center border-2 border-dashed border-border rounded-lg p-4 cursor-pointer transition-colors ${
          uploading ? "opacity-60" : "hover:border-accent/60"
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          e.dataTransfer.dropEffect = "copy";
        }}
        onDrop={(e) => {
          e.preventDefault();
          // dataTransfer.files is a FileList — convert to a real array.
          const dropped = Array.from(e.dataTransfer.files ?? []);
          if (dropped.length) onUpload(dropped);
        }}
      >
        <input
          ref={fileRef}
          type="file"
          multiple
          className="hidden"
          accept=".pdf,.txt,.md"
          onChange={(e) => {
            const picked = Array.from(e.target.files ?? []);
            if (picked.length) onUpload(picked);
          }}
          disabled={uploading}
        />
        <span className="text-sm">
          {uploading
            ? "Uploading + indexing…"
            : "Click or drop one or more files to upload"}
        </span>
        <span className="text-xs text-slate-400 mt-1">
          Files are chunked, embedded, and stored locally in ChromaDB.
        </span>
      </label>

      {errors.length > 0 && (
        <ul className="mt-2 space-y-1">
          {errors.map((e, i) => (
            <li key={i} className="text-xs text-red-400">
              <span className="font-medium">{e.filename}:</span> {e.error}
            </li>
          ))}
        </ul>
      )}

      <ul className="mt-3 space-y-2">
        {loading && <li className="text-xs text-slate-400">Loading…</li>}
        {!loading && docs.length === 0 && (
          <li className="text-xs text-slate-400">No documents yet.</li>
        )}
        {docs.map((d) => (
          <li
            key={d.doc_id}
            className="flex items-center justify-between bg-bg/50 border border-border rounded-md px-3 py-2"
          >
            <div className="min-w-0">
              <div className="text-sm truncate">{d.doc_name}</div>
              <div className="text-xs text-slate-400">
                {d.num_chunks} chunk{d.num_chunks === 1 ? "" : "s"}
              </div>
            </div>
            <button
              className="text-xs text-slate-400 hover:text-red-400"
              onClick={() => onDelete(d.doc_id)}
              title="Remove from KB"
            >
              Remove
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
