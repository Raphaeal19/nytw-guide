import { useState, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { CalendarView } from "../components/CalendarView";
import { EventHeader } from "../components/EventHeader";
import { PersonCard } from "../components/PersonCard";
import { MetModal } from "../components/MetModal";
import { AddEventModal } from "../components/AddEventModal";
import { CameraCapture } from "../components/CameraCapture";
import { IdentifyResult } from "../components/IdentifyResult";
import { useEvents } from "../hooks/useEvents";
import { usePeople } from "../hooks/usePeople";
import { useIdentify } from "../hooks/useIdentify";
import type { AttendancePerson } from "../types";

export function EventDetail() {
  const { eventId } = useParams<{ eventId: string }>();
  const navigate = useNavigate();
  const { events, loading: eventsLoading, createEvent } = useEvents();
  const { people, loading: peopleLoading, toggleMet, refetch } = usePeople(eventId);

  const [metTarget, setMetTarget] = useState<AttendancePerson | null>(null);
  const [showAddEvent, setShowAddEvent] = useState(false);
  const [search, setSearch] = useState("");
  const [filterMet, setFilterMet] = useState<"all" | "met" | "unmet">("all");
  const [showCamera, setShowCamera] = useState(false);
  const { run: runIdentify, loading: identifying, result: identifyResult, reset: resetIdentify } = useIdentify();

  const activeEvent = events.find((e) => e.id === eventId);

  const filtered = useMemo(() => {
    let list = people;
    if (filterMet === "met") list = list.filter((p) => p.met);
    if (filterMet === "unmet") list = list.filter((p) => !p.met);
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          (p.company ?? "").toLowerCase().includes(q) ||
          (p.role ?? "").toLowerCase().includes(q)
      );
    }
    return list;
  }, [people, filterMet, search]);

  const handleMetToggle = (person: AttendancePerson) => {
    if (person.met) {
      toggleMet(person.attendance_id, false);
    } else {
      setMetTarget(person);
    }
  };

  // Called by MetModal at the notes step — toggles met but does NOT close the modal
  const handleMetMarked = async (notes: string, selfieUrl?: string) => {
    if (!metTarget) return;
    await toggleMet(metTarget.attendance_id, true, notes, selfieUrl);
  };

  // Called by MetModal when the whole flow is done/cancelled
  const handleModalClose = () => {
    setMetTarget(null);
    refetch();
  };

  if (eventsLoading) return <div className="loading">Loading…</div>;

  if (events.length === 0) {
    return (
      <div className="empty-screen">
        <p>No events yet.</p>
        <button className="btn btn--primary" onClick={() => setShowAddEvent(true)}>
          Add your first event
        </button>
        {showAddEvent && (
          <AddEventModal
            onCreate={async (data) => {
              const ev = await createEvent(data);
              setShowAddEvent(false);
              navigate(`/events/${ev.id}`);
            }}
            onClose={() => setShowAddEvent(false)}
          />
        )}
      </div>
    );
  }

  return (
    <div className="app-layout">
      <CalendarView
        events={events}
        activeId={eventId}
        onSelectEvent={(id) => navigate(`/events/${id}`)}
        onAdd={() => setShowAddEvent(true)}
      />

      {activeEvent ? (
        <>
          <EventHeader event={activeEvent} />

          <div className="people-toolbar">
            <input
              className="search-input"
              type="search"
              placeholder="Search people…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <div className="filter-pills">
              {(["all", "met", "unmet"] as const).map((f) => (
                <button
                  key={f}
                  className={`filter-pill ${filterMet === f ? "filter-pill--active" : ""}`}
                  onClick={() => setFilterMet(f)}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>

          {peopleLoading ? (
            <div className="loading">Loading attendees…</div>
          ) : filtered.length === 0 ? (
            <p className="empty-state">
              {people.length === 0
                ? "No attendees yet — run the agent pipeline to populate this event."
                : "No matches."}
            </p>
          ) : (
            <div className="people-grid">
              {filtered.map((p) => (
                <PersonCard
                  key={p.attendance_id}
                  person={p}
                  eventId={eventId!}
                  onMetToggle={handleMetToggle}
                />
              ))}
            </div>
          )}
        </>
      ) : (
        <p className="empty-state">Select an event above.</p>
      )}

      {metTarget && (
        <MetModal
          person={metTarget}
          onMetMarked={handleMetMarked}
          onClose={handleModalClose}
        />
      )}

      {showAddEvent && (
        <AddEventModal
          onCreate={async (data) => {
            const ev = await createEvent(data);
            setShowAddEvent(false);
            navigate(`/events/${ev.id}`);
          }}
          onClose={() => setShowAddEvent(false)}
        />
      )}

      {eventId && (
        <button
          className="identify-fab"
          onClick={() => { resetIdentify(); setShowCamera(true); }}
        >
          &#128247;
        </button>
      )}

      {showCamera && !identifyResult && (
        <CameraCapture
          onCapture={(blob) => {
            if (eventId) runIdentify(eventId, blob);
          }}
          onClose={() => setShowCamera(false)}
        />
      )}

      {showCamera && identifying && (
        <div className="camera-overlay">
          <div className="identify-loading">Identifying...</div>
        </div>
      )}

      {showCamera && identifyResult && !identifying && (
        <IdentifyResult
          match={identifyResult.match}
          confidence={identifyResult.confidence}
          eventId={eventId!}
          error={identifyResult.error}
          onRetry={() => { resetIdentify(); }}
          onClose={() => { setShowCamera(false); resetIdentify(); }}
        />
      )}
    </div>
  );
}
