import { useState, useEffect, useCallback } from "react";
import { people as peopleApi, attendance as attendanceApi } from "../api/client";
import { enqueue, isNetworkError } from "../lib/offlineQueue";
import type { AttendancePerson } from "../types";

export function usePeople(eventId: string | undefined) {
  const [data, setData] = useState<AttendancePerson[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    if (!eventId) return;
    setLoading(true);
    try {
      setError(null);
      const result = await peopleApi.listForEvent(eventId);
      setData(result);
    } catch {
      setError("Failed to load attendees");
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => { fetch(); }, [fetch]);

  const toggleMet = useCallback(
    async (attendanceId: string, met: boolean, notes?: string) => {
      // Optimistic update
      setData((prev) =>
        prev.map((p) =>
          p.attendance_id === attendanceId
            ? { ...p, met, met_notes: notes ?? p.met_notes, met_at: met ? new Date().toISOString() : p.met_at }
            : p
        )
      );
      try {
        const updated = await attendanceApi.setMet(attendanceId, met, notes);
        setData((prev) =>
          prev.map((p) =>
            p.attendance_id === attendanceId ? { ...p, ...updated } : p
          )
        );
      } catch (err) {
        if (isNetworkError(err)) {
          // Offline — keep optimistic state, queue for later
          enqueue(attendanceId, met, notes);
        } else {
          // Server error — roll back
          fetch();
        }
      }
    },
    [fetch]
  );

  return { people: data, loading, error, refetch: fetch, toggleMet };
}
