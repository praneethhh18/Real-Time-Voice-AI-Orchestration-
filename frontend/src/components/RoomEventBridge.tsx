import { useEffect } from "react";
import { useRoomContext } from "@livekit/components-react";
import {
  RoomEvent,
  type Participant,
  type TranscriptionSegment,
} from "livekit-client";
import type { TranscriptEntry } from "./Transcript";
import type { RagSource } from "../lib/api";
import { InRoomCallControls } from "./VoiceCall";

/**
 * Bridges LiveKit room events into React-state callbacks.
 *
 * 1. STT/TTS transcription events  -> onTranscript()
 *    LiveKit's agents framework publishes both user STT and agent TTS as
 *    transcription segments on the room, with `final` flagged correctly.
 *
 * 2. Custom data-channel messages -> onRagSources()
 *    Our voice agent publishes a JSON blob on topic="rag" each turn with
 *    the chunks it retrieved. We decode and forward.
 *
 * Mounted inside <LiveKitRoom> so `useRoomContext` works.
 */
export function RoomEventBridge({
  onTranscript,
  onRagSources,
}: {
  onTranscript: (entry: TranscriptEntry) => void;
  onRagSources: (query: string, sources: RagSource[]) => void;
}) {
  const room = useRoomContext();

  useEffect(() => {
    if (!room) return;

    const handleTranscription = (
      segments: TranscriptionSegment[],
      participant?: Participant,
    ) => {
      const isAgent = participant ? participant.isAgent : false;
      for (const seg of segments) {
        onTranscript({
          id: seg.id,
          role: isAgent ? "agent" : "user",
          text: seg.text,
          final: seg.final,
        });
      }
    };

    const handleData = (
      payload: Uint8Array,
      _participant?: Participant,
      _kind?: unknown,
      topic?: string,
    ) => {
      if (topic !== "rag") return;
      try {
        const msg = JSON.parse(new TextDecoder().decode(payload));
        if (msg.type === "rag_sources") {
          onRagSources(msg.query ?? "", msg.sources ?? []);
        }
      } catch (e) {
        // Bad JSON shouldn't crash the UI.
        console.warn("Could not parse RAG sources payload", e);
      }
    };

    room.on(RoomEvent.TranscriptionReceived, handleTranscription);
    room.on(RoomEvent.DataReceived, handleData);

    return () => {
      room.off(RoomEvent.TranscriptionReceived, handleTranscription);
      room.off(RoomEvent.DataReceived, handleData);
    };
  }, [room, onTranscript, onRagSources]);

  // While we're inside the room, also render the floating mic + visualizer.
  return <InRoomCallControls />;
}
