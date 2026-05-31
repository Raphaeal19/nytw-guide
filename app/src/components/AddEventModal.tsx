import { useState } from "react";
import type { Event } from "../types";

interface Props {
  onCreate: (data: Partial<Event>) => Promise<void>;
  onClose: () => void;
}

const COLORS = ["#7F77DD", "#DD7777", "#77DDBB", "#DDC277", "#77AADD", "#DD77AA", "#888"];

export function AddEventModal({ onCreate, onClose }: Props) {
  const [name, setName] = useState("");
  const [dateStart, setDateStart] = useState("");
  const [dateEnd, setDateEnd] = useState("");
  const [location, setLocation] = useState("");
  const [tags, setTags] = useState("");
  const [color, setColor] = useState(COLORS[0]);
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setSaving(true);
    try {
      await onCreate({
        name: name.trim(),
        date_start: dateStart || null,
        date_end: dateEnd || null,
        location: location.trim() || null,
        tags: tags ? tags.split(",").map((t) => t.trim()).filter(Boolean) : null,
        color,
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <button className="modal__close" onClick={onClose}>✕</button>
        <h2 className="modal__title">New event</h2>
        <form onSubmit={handleSubmit} className="add-event-form">
          <label className="form-label">
            Name *
            <input
              className="form-input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="SaaStr Annual 2025"
              required
              autoFocus
            />
          </label>
          <div className="form-row">
            <label className="form-label">
              Start date
              <input className="form-input" type="date" value={dateStart} onChange={(e) => setDateStart(e.target.value)} />
            </label>
            <label className="form-label">
              End date
              <input className="form-input" type="date" value={dateEnd} onChange={(e) => setDateEnd(e.target.value)} />
            </label>
          </div>
          <label className="form-label">
            Location
            <input className="form-input" value={location} onChange={(e) => setLocation(e.target.value)} placeholder="San Francisco" />
          </label>
          <label className="form-label">
            Tags (comma-separated)
            <input className="form-input" value={tags} onChange={(e) => setTags(e.target.value)} placeholder="SaaS, B2B, Founders" />
          </label>
          <div className="form-label">
            Color
            <div className="color-swatches">
              {COLORS.map((c) => (
                <button
                  key={c}
                  type="button"
                  className={`color-swatch ${color === c ? "color-swatch--active" : ""}`}
                  style={{ background: c }}
                  onClick={() => setColor(c)}
                />
              ))}
            </div>
          </div>
          <button className="btn btn--primary btn--full" type="submit" disabled={saving || !name.trim()}>
            {saving ? "Creating…" : "Create event"}
          </button>
        </form>
      </div>
    </div>
  );
}
