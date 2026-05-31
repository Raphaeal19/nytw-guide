import { useState } from "react";
import type { AttendancePerson } from "../types";
import { useOutreach } from "../hooks/useOutreach";

interface Props {
  person: AttendancePerson;
  onSent: () => void;
}

const CHANNELS = [
  { id: "linkedin", label: "LinkedIn DM", requires: "linkedin_url" },
  { id: "email", label: "Email", requires: "email" },
  { id: "twitter", label: "Twitter DM", requires: "twitter_handle" },
] as const;

export function OutreachPanel({ person, onSent }: Props) {
  const [channel, setChannel] = useState<string>(
    person.outreach_channel ?? "linkedin"
  );
  const [message, setMessage] = useState(person.outreach_draft ?? "");
  const { draft, send, drafting, sending, error } = useOutreach();

  if (!person.met) {
    return (
      <div className="section">
        <p className="empty-state">Mark this person as met first to draft a follow-up.</p>
      </div>
    );
  }

  if (person.outreach_sent) {
    return (
      <div className="section">
        <div className="outreach-sent">
          <p className="outreach-sent__label">✓ Sent via {person.outreach_channel}</p>
          {person.outreach_sent_at && (
            <p className="outreach-sent__when">
              {new Date(person.outreach_sent_at).toLocaleDateString()}
            </p>
          )}
          {person.outreach_draft && (
            <blockquote className="outreach-sent__msg">{person.outreach_draft}</blockquote>
          )}
        </div>
      </div>
    );
  }

  const availableChannels = CHANNELS.filter(
    (c) => person[c.requires as keyof AttendancePerson]
  );

  const handleDraft = async () => {
    const text = await draft(person.attendance_id, channel);
    if (text) setMessage(text);
  };

  const handleSend = async () => {
    const ok = await send(person.attendance_id, channel, message);
    if (ok) onSent();
  };

  return (
    <div className="section">
      <div className="section__block">
        <h3 className="section__label">Channel</h3>
        <div className="channel-pills">
          {availableChannels.map((c) => (
            <button
              key={c.id}
              className={`channel-pill ${channel === c.id ? "channel-pill--active" : ""}`}
              onClick={() => setChannel(c.id)}
            >
              {c.label}
            </button>
          ))}
        </div>
      </div>

      <div className="section__block">
        <div className="outreach-header">
          <h3 className="section__label">Message</h3>
          <button
            className="btn btn--sm"
            onClick={handleDraft}
            disabled={drafting}
          >
            {drafting ? "Drafting…" : message ? "Re-draft" : "Draft"}
          </button>
        </div>
        <textarea
          className="modal__textarea modal__textarea--draft"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Draft a message or click Draft to generate one…"
          rows={6}
        />
      </div>

      {error && <p className="modal__error">{error}</p>}

      <button
        className="btn btn--primary btn--full"
        onClick={handleSend}
        disabled={sending || !message}
      >
        {sending ? "Sending…" : "Send"}
      </button>
    </div>
  );
}
