import { useState } from "react";
import { identify } from "../api/client";
import type { AttendancePerson } from "../types";

interface IdentifyResult {
  match: AttendancePerson | null;
  confidence: number;
  error?: string;
}

export function useIdentify() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<IdentifyResult | null>(null);

  const run = async (eventId: string, imageBlob: Blob) => {
    setLoading(true);
    setResult(null);
    try {
      const data = await identify.match(eventId, imageBlob);
      setResult({
        match: data.match,
        confidence: data.confidence,
        error: (data as any).error,
      });
    } catch {
      setResult({ match: null, confidence: 0, error: "Failed to identify" });
    } finally {
      setLoading(false);
    }
  };

  const reset = () => setResult(null);

  return { run, loading, result, reset };
}
