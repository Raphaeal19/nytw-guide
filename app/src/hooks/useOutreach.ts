import { useState, useCallback } from "react";
import { outreach as outreachApi } from "../api/client";

export function useOutreach() {
  const [drafting, setDrafting] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const draft = useCallback(
    async (attendanceId: string, channel: string, extraContext?: string) => {
      setDrafting(true);
      setError(null);
      try {
        const result = await outreachApi.draft(attendanceId, channel, extraContext);
        return result.draft;
      } catch {
        setError("Failed to generate draft");
        return null;
      } finally {
        setDrafting(false);
      }
    },
    []
  );

  const send = useCallback(
    async (attendanceId: string, channel: string, message: string) => {
      setSending(true);
      setError(null);
      try {
        const result = await outreachApi.send(attendanceId, channel, message);
        // Poll for completion
        let attempts = 0;
        while (attempts < 20) {
          await new Promise((r) => setTimeout(r, 1500));
          const status = await outreachApi.status(result.task_id);
          if (status.status === "sent") return true;
          if (status.status === "failed") {
            setError(status.error ?? "Send failed");
            return false;
          }
          attempts++;
        }
        setError("Timed out waiting for send confirmation");
        return false;
      } catch {
        setError("Failed to send message");
        return false;
      } finally {
        setSending(false);
      }
    },
    []
  );

  return { draft, send, drafting, sending, error };
}
