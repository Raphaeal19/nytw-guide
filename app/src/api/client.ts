import axios from "axios";
import type { Event, AttendancePerson } from "../types";

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
  setMet: (attendanceId: string, met: boolean, notes?: string) =>
    api
      .post(`/attendance/${attendanceId}/met`, { met, notes })
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
};
