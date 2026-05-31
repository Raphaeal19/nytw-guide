import axios from "axios";

const QUEUE_KEY = "event-intel-offline-queue";

interface QueuedMutation {
  attendanceId: string;
  met: boolean;
  notes: string | undefined;
  timestamp: number;
}

function load(): QueuedMutation[] {
  try {
    return JSON.parse(localStorage.getItem(QUEUE_KEY) ?? "[]");
  } catch {
    return [];
  }
}

function save(q: QueuedMutation[]) {
  localStorage.setItem(QUEUE_KEY, JSON.stringify(q));
}

export function enqueue(attendanceId: string, met: boolean, notes: string | undefined) {
  const queue = load().filter((m) => m.attendanceId !== attendanceId);
  queue.push({ attendanceId, met, notes, timestamp: Date.now() });
  save(queue);
}

export function queueSize(): number {
  return load().length;
}

export async function flush(): Promise<number> {
  const queue = load();
  if (queue.length === 0) return 0;

  let flushed = 0;
  const remaining: QueuedMutation[] = [];

  for (const m of queue) {
    try {
      await axios.post(`/api/attendance/${m.attendanceId}/met`, {
        met: m.met,
        notes: m.notes,
      });
      flushed++;
    } catch {
      remaining.push(m);
    }
  }

  save(remaining);
  return flushed;
}

export function isNetworkError(err: unknown): boolean {
  return axios.isAxiosError(err) && !err.response;
}
