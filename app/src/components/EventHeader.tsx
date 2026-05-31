import type { Event } from "../types";

interface Props {
  event: Event;
}

function formatDateRange(start: string | null, end: string | null): string {
  if (!start) return "";
  const s = new Date(start).toLocaleDateString("en-US", { month: "short", day: "numeric" });
  if (!end || end === start) return s;
  const e = new Date(end).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  return `${s} – ${e}`;
}

export function EventHeader({ event }: Props) {
  const toMeet = event.people_count - event.met_count;

  return (
    <div className="event-header">
      <div className="event-header__top">
        <h1 className="event-header__name">{event.name}</h1>
        {event.location && (
          <p className="event-header__meta">
            {formatDateRange(event.date_start, event.date_end)}
            {event.date_start && event.location ? " · " : ""}
            {event.location}
          </p>
        )}
        {event.tags && event.tags.length > 0 && (
          <div className="event-header__tags">
            {event.tags.map((t) => (
              <span key={t} className="tag">{t}</span>
            ))}
          </div>
        )}
      </div>
      <div className="event-header__stats">
        <div className="stat">
          <span className="stat__n">{event.people_count}</span>
          <span className="stat__label">total</span>
        </div>
        <div className="stat">
          <span className="stat__n stat__n--met">{event.met_count}</span>
          <span className="stat__label">met</span>
        </div>
        <div className="stat">
          <span className="stat__n">{toMeet}</span>
          <span className="stat__label">to meet</span>
        </div>
      </div>
    </div>
  );
}
