import { useNavigate } from "react-router-dom";
import type { Event } from "../types";

interface Props {
  events: Event[];
  activeId: string | undefined;
  onAdd: () => void;
}

export function EventTabs({ events, activeId, onAdd }: Props) {
  const navigate = useNavigate();

  return (
    <div className="event-tabs">
      <div className="tabs-scroll">
        {events.map((ev) => (
          <button
            key={ev.id}
            className={`tab ${ev.id === activeId ? "tab--active" : ""}`}
            onClick={() => navigate(`/events/${ev.id}`)}
          >
            <span
              className="tab-dot"
              style={{ background: ev.color ?? "#888" }}
            />
            <span className="tab-name">{ev.name}</span>
            {ev.people_count > 0 && (
              <span className="tab-badge">{ev.people_count}</span>
            )}
          </button>
        ))}
        <button className="tab tab--add" onClick={onAdd}>
          +
        </button>
      </div>
    </div>
  );
}
