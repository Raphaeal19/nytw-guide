import { useState, useEffect, useCallback } from "react";
import { events as eventsApi } from "../api/client";
import type { Event } from "../types";

export function useEvents() {
  const [data, setData] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    try {
      setError(null);
      const result = await eventsApi.list();
      setData(result);
    } catch {
      setError("Failed to load events");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  const createEvent = useCallback(async (payload: Partial<Event>) => {
    const created = await eventsApi.create(payload);
    setData((prev) => [created, ...prev]);
    return created;
  }, []);

  return { events: data, loading, error, refetch: fetch, createEvent };
}
