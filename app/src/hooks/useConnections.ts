import { useEffect, useState } from "react";
import { settings } from "../api/client";
import type { ServiceConnection } from "../types";

export function useConnections() {
  const [connections, setConnections] = useState<ServiceConnection[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    settings
      .connections()
      .then(setConnections)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return { connections, loading };
}
