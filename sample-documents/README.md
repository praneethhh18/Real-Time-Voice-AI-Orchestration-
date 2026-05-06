# Sample Documents

These two files are intentionally about a **fictional product** ("Aurora
Sleep Mask" by "Helix Wellness Labs") so that the LLM has no prior knowledge
to fall back on. Every fact in these documents is invented. That makes the
RAG demo unambiguous: if the agent answers correctly, it can only be
because retrieval worked.

## Files

- `aurora_sleep_mask_handbook.md` — Detailed product spec (3 SKUs, prices,
  battery life, warranty, sleep-tracking specs, return policy, etc.).
- `helix_company_faq.md` — Short FAQ about the parent company (HQ, founding
  year, payment methods, shipping policy, support hours).

## Suggested demo questions (each one is grounded in the docs)

Pick 1-2 of these for the recorded demo. The agent must answer them
correctly *only* by retrieving from the uploaded docs.

- **"How long is the warranty on the Aurora Pro Max?"**
  → 12-month standard, 24 months for Aurora Care members.

- **"What's the battery life of the Aurora Pro?"**
  → 48 hours.

- **"How much does the Aurora Lite cost?"**
  → $79.

- **"Where is Helix Wellness Labs based?"**
  → Bengaluru, India (HQ); Coimbatore manufacturing; Lisbon R&D.

- **"How does the Aurora Care subscription work?"**
  → $9/month; 24-month extended warranty on Pro Max, annual fabric
  replacement, priority 24-hour support.

- **"Can children use the Aurora Pro Max?"**
  → No — children under 12 should not use Pro or Pro Max because the IMU
  haptic motors can exceed pediatric guidance.

- **"When was Helix Wellness Labs founded and by whom?"**
  → 2021, by Dr. Meera Ranganathan and Tomás Almeida.

## How to use them in the demo

1. Open the app at http://localhost:5173.
2. In the Knowledge Base panel, drag-and-drop both files (or upload them
   one at a time).
3. Confirm both appear in the document list with chunk counts.
4. Click **Start Call** and grant microphone permission.
5. Ask one of the questions above.
6. Watch the **RAG Sources** panel populate with the retrieved chunks
   (you should see the relevant section of the doc with a high score).
7. Listen for the agent's spoken answer — it should match the doc.
