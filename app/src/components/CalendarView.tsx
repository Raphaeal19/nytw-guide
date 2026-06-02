import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import type { Event } from "../types";

interface Props {
  events: Event[];
  activeId: string | undefined;
  onSelectEvent: (id: string) => void;
  onAdd: () => void;
}

const DAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function sameDay(a: Date, b: Date) {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

function parseDate(s: string) {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
}

function eventOnDay(ev: Event, day: Date): boolean {
  if (!ev.date_start) return false;
  const start = parseDate(ev.date_start);
  if (!ev.date_end) return sameDay(start, day);
  const end = parseDate(ev.date_end);
  return day >= start && day <= end;
}

function formatMonth(d: Date) {
  return d.toLocaleDateString("en-US", { month: "long", year: "numeric" });
}

export function CalendarView({ events, activeId, onSelectEvent, onAdd }: Props) {
  const navigate = useNavigate();

  const initialMonth = useMemo(() => {
    const active = events.find((e) => e.id === activeId);
    if (active?.date_start) {
      const d = parseDate(active.date_start);
      return new Date(d.getFullYear(), d.getMonth(), 1);
    }
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1);
  }, [events, activeId]);

  const [month, setMonth] = useState(initialMonth);
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);

  const today = useMemo(() => {
    const n = new Date();
    return new Date(n.getFullYear(), n.getMonth(), n.getDate());
  }, []);

  const days = useMemo(() => {
    const year = month.getFullYear();
    const m = month.getMonth();
    const firstDay = new Date(year, m, 1).getDay();
    const daysInMonth = new Date(year, m + 1, 0).getDate();

    const cells: (Date | null)[] = [];
    for (let i = 0; i < firstDay; i++) cells.push(null);
    for (let d = 1; d <= daysInMonth; d++) cells.push(new Date(year, m, d));
    return cells;
  }, [month]);

  const eventsForDay = useMemo(() => {
    if (!selectedDate) return [];
    return events.filter((ev) => eventOnDay(ev, selectedDate));
  }, [events, selectedDate]);

  const unscheduled = useMemo(
    () => events.filter((ev) => !ev.date_start),
    [events],
  );

  const eventsOnDay = (day: Date) => events.filter((ev) => eventOnDay(ev, day));

  const prevMonth = () =>
    setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1));
  const nextMonth = () =>
    setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1));

  return (
    <div className="calendar">
      <div className="calendar__header">
        <button className="btn calendar__nav" onClick={prevMonth}>
          &lsaquo;
        </button>
        <span className="calendar__month">{formatMonth(month)}</span>
        <button className="btn calendar__nav" onClick={nextMonth}>
          &rsaquo;
        </button>
        <button className="btn calendar__add" onClick={onAdd}>
          +
        </button>
        <button
          className="btn calendar__settings"
          onClick={() => navigate("/settings")}
        >
          &#9881;
        </button>
      </div>

      <div className="calendar__grid">
        {DAY_LABELS.map((d) => (
          <div key={d} className="calendar__day-label">
            {d}
          </div>
        ))}
        {days.map((day, i) => {
          if (!day) return <div key={`pad-${i}`} className="calendar__cell calendar__cell--pad" />;
          const dayEvents = eventsOnDay(day);
          const isToday = sameDay(day, today);
          const isSelected = selectedDate ? sameDay(day, selectedDate) : false;

          return (
            <button
              key={day.getTime()}
              className={[
                "calendar__cell",
                isToday && "calendar__cell--today",
                isSelected && "calendar__cell--selected",
                dayEvents.length > 0 && "calendar__cell--has-events",
              ]
                .filter(Boolean)
                .join(" ")}
              onClick={() => setSelectedDate(day)}
            >
              <span className="calendar__date">{day.getDate()}</span>
              {dayEvents.length > 0 && (
                <div className="calendar__dots">
                  {dayEvents.slice(0, 3).map((ev) => (
                    <span
                      key={ev.id}
                      className="calendar__dot"
                      style={{ background: ev.color ?? "#888" }}
                    />
                  ))}
                </div>
              )}
            </button>
          );
        })}
      </div>

      {selectedDate && eventsForDay.length > 0 && (
        <div className="calendar__day-events">
          <h3 className="calendar__day-title">
            {selectedDate.toLocaleDateString("en-US", {
              weekday: "short",
              month: "short",
              day: "numeric",
            })}
          </h3>
          {eventsForDay.map((ev) => (
            <button
              key={ev.id}
              className={`calendar__event-item ${ev.id === activeId ? "calendar__event-item--active" : ""}`}
              onClick={() => onSelectEvent(ev.id)}
            >
              <span
                className="calendar__event-dot"
                style={{ background: ev.color ?? "#888" }}
              />
              <div className="calendar__event-info">
                <span className="calendar__event-name">{ev.name}</span>
                {ev.location && (
                  <span className="calendar__event-loc">{ev.location}</span>
                )}
              </div>
              <span className="calendar__event-count">
                {ev.people_count} people
              </span>
            </button>
          ))}
        </div>
      )}

      {selectedDate && eventsForDay.length === 0 && (
        <div className="calendar__day-events">
          <p className="calendar__empty">No events on this day</p>
        </div>
      )}

      {unscheduled.length > 0 && (
        <div className="calendar__day-events">
          <h3 className="calendar__day-title">Unscheduled</h3>
          {unscheduled.map((ev) => (
            <button
              key={ev.id}
              className={`calendar__event-item ${ev.id === activeId ? "calendar__event-item--active" : ""}`}
              onClick={() => onSelectEvent(ev.id)}
            >
              <span
                className="calendar__event-dot"
                style={{ background: ev.color ?? "#888" }}
              />
              <div className="calendar__event-info">
                <span className="calendar__event-name">{ev.name}</span>
              </div>
              <span className="calendar__event-count">
                {ev.people_count} people
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
