import { useEffect, useState } from "react";
import { fetchPrompt, updatePrompt } from "../lib/api";

/**
 * Editable system prompt.
 *
 * Saved prompts apply to the NEXT call (the agent reads the prompt at
 * session start). We disable the textarea while a call is in progress to
 * make this contract obvious.
 */
export function PromptEditor({ disabled }: { disabled: boolean }) {
  const [value, setValue] = useState("");
  const [savedValue, setSavedValue] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<Date | null>(null);

  useEffect(() => {
    fetchPrompt()
      .then((p) => {
        setValue(p.system_prompt);
        setSavedValue(p.system_prompt);
      })
      .finally(() => setLoading(false));
  }, []);

  async function save() {
    setSaving(true);
    try {
      const res = await updatePrompt(value);
      setValue(res.system_prompt);
      setSavedValue(res.system_prompt);
      setSavedAt(new Date());
    } finally {
      setSaving(false);
    }
  }

  const dirty = value !== savedValue;

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-2">
        <h2 className="font-semibold">System Prompt</h2>
        {savedAt && !dirty && (
          <span className="text-xs text-green-400">
            Saved · {savedAt.toLocaleTimeString()}
          </span>
        )}
        {dirty && <span className="text-xs text-amber-300">Unsaved</span>}
      </div>

      <textarea
        className="input min-h-[160px] font-mono text-xs leading-relaxed"
        value={loading ? "Loading…" : value}
        onChange={(e) => setValue(e.target.value)}
        disabled={loading || disabled}
        placeholder="Tell the agent how to behave…"
      />

      <div className="flex items-center justify-between mt-2 text-xs text-slate-400">
        <span>
          {disabled
            ? "End the call to edit. Changes apply to the next call."
            : "Changes apply to the next call you start."}
        </span>
        <button
          className="btn-primary text-sm"
          onClick={save}
          disabled={loading || saving || disabled || !dirty}
        >
          {saving ? "Saving…" : "Save"}
        </button>
      </div>
    </div>
  );
}
