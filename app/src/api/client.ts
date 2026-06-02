import axios from "axios";
import type { Event, AttendancePerson, ServiceConnection } from "../types";

const api = axios.create({ baseURL: "/api" });

export const events = {
  list: () => api.get<Event[]>("/events").then((r) => r.data),
  get: (id: string) => api.get<Event>(`/events/${id}`).then((r) => r.data),
  create: (data: Partial<Event>) =>
    api.post<Event>("/events", data).then((r) => r.data),
};

export const people = {
  listForEvent: (eventId: string, params?: { met?: boolean; q?: string }) =>
    api
      .get<AttendancePerson[]>(`/events/${eventId}/people`, { params })
      .then((r) => r.data),
  get: (personId: string) =>
    api.get(`/people/${personId}`).then((r) => r.data),
};

export const attendance = {
  setMet: (attendanceId: string, met: boolean, notes?: string, selfieUrl?: string) =>
    api
      .post(`/attendance/${attendanceId}/met`, {
        met,
        notes,
        selfie_url: selfieUrl,
      })
      .then((r) => r.data),
};

export const outreach = {
  draft: (attendanceId: string, channel: string, extraContext?: string) =>
    api
      .post<{ draft: string }>("/outreach/draft", {
        attendance_id: attendanceId,
        channel,
        extra_context: extraContext,
      })
      .then((r) => r.data),
  send: (attendanceId: string, channel: string, message: string) =>
    api
      .post<{ task_id: string; status: string }>("/outreach/send", {
        attendance_id: attendanceId,
        channel,
        message,
      })
      .then((r) => r.data),
  status: (taskId: string) =>
    api
      .get<{ status: string; error?: string }>(`/outreach/status/${taskId}`)
      .then((r) => r.data),
  polishNotes: (rawNotes: string, personName: string) =>
    api
      .post<{ polished: string }>("/outreach/polish-notes", {
        raw_notes: rawNotes,
        person_name: personName,
      })
      .then((r) => r.data),
};

export const settings = {
  connections: () =>
    api.get<ServiceConnection[]>("/settings/connections").then((r) => r.data),
};

export const identify = {
  match: (eventId: string, image: Blob) => {
    const fd = new FormData();
    fd.append("image", image, "capture.jpg");
    return api
      .post<{ match: AttendancePerson | null; confidence: number }>(
        `/events/${eventId}/identify`,
        fd,
      )
      .then((r) => r.data);
  },
};

export const upload = {
  selfie: (image: Blob) => {
    const fd = new FormData();
    fd.append("image", image, "selfie.jpg");
    return api.post<{ url: string }>("/upload/selfie", fd).then((r) => r.data);
  },
};
