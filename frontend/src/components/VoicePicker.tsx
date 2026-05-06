import { useEffect, useState } from "react";
import { fetchVoice, updateVoice, type VoiceOption } from "../lib/api";

/**
 * TTS voice picker. The agent reads the selected voice at session start,
 * so changes apply to the next call (same contract as the system prompt).
 */
export function VoicePicker({ disabled }: { disabled: boolean }) {
  const [available, setAvailable] = useState<VoiceOption[]>([]);
  const [current, setCurrent] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<Date | null>(null);

  useEffect(() => {
    fetchVoice()
      .then((v) => {
        setAvailable(v.available);
        setCurrent(v.current);
      })
      .finally(() => setLoading(false));
  }, []);

  async function onChange(id: string) {
    setSaving(true);
    try {
      const res = await updateVoice(id);
      setCurrent(res.current);
      setSavedAt(new Date());
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-2">
        <h2 className="font-semibold">Agent Voice</h2>
        {savedAt && (
          <span className="text-xs text-green-400">
            Saved · {savedAt.toLocaleTimeString()}
          </span>
        )}
      </div>

      <select
        className="input"
        value={current}
        onChange={(e) => onChange(e.target.value)}
        disabled={loading || saving || disabled}
      >
        {available.map((v) => (
          <option key={v.id} value={v.id}>
            {v.label}
          </option>
        ))}
      </select>

      <p className="text-xs text-slate-400 mt-2">
        {disabled
          ? "End the call to change the voice. Applies to next call."
          : "Change applies to the next call you start."}
      </p>
    </div>
  );
}
