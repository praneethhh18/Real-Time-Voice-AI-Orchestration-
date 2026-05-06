// Tiny typed wrapper around fetch — keeps API calls in one place so we can
// swap base URL or add auth later without hunting through components.

const BASE = ""; // same-origin via Vite proxy in dev; nginx routes /api in prod

export type TokenResponse = {
  token: string;
  url: string;
  room: string;
  identity: string;
};

export type KbDocument = {
  doc_id: string;
  doc_name: string;
  num_chunks: number;
};

export type RagSource = {
  text: string;
  doc_name: string;
  doc_id: string;
  chunk_index: number;
  score: number;
};

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return res.json();
}

export async function fetchToken(): Promise<TokenResponse> {
  return handle(
    await fetch(`${BASE}/api/token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    }),
  );
}

export async function fetchPrompt(): Promise<{ system_prompt: string }> {
  return handle(await fetch(`${BASE}/api/prompt`));
}

export async function updatePrompt(system_prompt: string) {
  return handle<{ system_prompt: string }>(
    await fetch(`${BASE}/api/prompt`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ system_prompt }),
    }),
  );
}

export async function listDocuments(): Promise<KbDocument[]> {
  return handle(await fetch(`${BASE}/api/kb/documents`));
}

export type UploadResult = {
  doc_id: string;
  doc_name: string;
  num_chunks: number;
  char_count: number;
};

export type UploadResponse = {
  results: UploadResult[];
  errors: { filename: string; error: string }[];
};

// Accepts one or many files in a single request. Per-file errors are
// returned in `errors` rather than thrown, so a single bad file doesn't
// hide the success of the others.
export async function uploadDocuments(files: File[]): Promise<UploadResponse> {
  const fd = new FormData();
  for (const f of files) fd.append("files", f);
  return handle<UploadResponse>(
    await fetch(`${BASE}/api/kb/upload`, { method: "POST", body: fd }),
  );
}

export async function deleteDocument(doc_id: string) {
  return handle(
    await fetch(`${BASE}/api/kb/documents/${doc_id}`, { method: "DELETE" }),
  );
}

// --- Voice picker ---
export type VoiceOption = { id: string; label: string };
export type VoiceState = { current: string; available: VoiceOption[] };

export async function fetchVoice(): Promise<VoiceState> {
  return handle(await fetch(`${BASE}/api/voice`));
}

export async function updateVoice(voice_id: string): Promise<VoiceState> {
  return handle<VoiceState>(
    await fetch(`${BASE}/api/voice`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ voice_id }),
    }),
  );
}
