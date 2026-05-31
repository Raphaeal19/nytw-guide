import { useState } from "react";
import type { AttendancePerson } from "../types";
import { useOutreach } from "../hooks/useOutreach";

interface Props {
  person: AttendancePerson;
  onMetMarked: (notes: string) => Promise<void>;
  onClose: () => void;
}

type Step = "confirm" | "notes" | "channel" | "draft" | "done";

const CHANNELS = [
  { id: "linkedin", label: "LinkedIn DM", requires: "linkedin_url" },
  { id: "email",    label: "Email",        requires: "email" },
  { id: "twitter",  label: "Twitter DM",  requires: "twitter_handle" },
] as const;

export function MetModal({ person, onMetMarked, onClose }: Props) {
  const [step, setStep]           = useState<Step>("confirm");
  const [notes, setNotes]         = useState(person.met_notes ?? "");
  const [channel, setChannel]     = useState<string | null>(null);
  const [draftText, setDraftText] = useState("");
  const [marking, setMarking]     = useState(false);
  const { draft, send, drafting, sending, error } = useOutreach();

  const availableChannels = CHANNELS.filter(
    (c) => person[c.requires as keyof AttendancePerson]
  );

  const topPoint = person.talking_points
    ?.slice()
    .sort((a, b) => a.priority - b.priority)[0]?.text;

  // Step 1: just advance internally — do NOT call onMetMarked yet
  const handleConfirmStep = () => setStep("notes");

  // Step 2: mark met with notes, then advance
  const handleNotesNext = async () => {
    setMarking(true);
    try {
      await onMetMarked(notes);
      setStep(availableChannels.length > 0 ? "channel" : "done");
    } finally {
      setMarking(false);
    }
  };

  const handleChannelSelect = async (ch: string) => {
    setChannel(ch);
    setStep("draft");
    const text = await draft(person.attendance_id, ch, notes || undefined);
    if (text) setDraftText(text);
  };

  const handleSend = async () => {
    if (!channel) return;
    const ok = await send(person.attendance_id, channel, draftText);
    if (ok) setStep("done");
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <button className="modal__close" onClick={onClose}>✕</button>

        {step === "confirm" && (
          <div className="modal__step">
            <h2 className="modal__title">You met {person.name}</h2>
            <p className="modal__sub">
              {[person.role, person.company].filter(Boolean).join(" at ")}
            </p>
            <div className="modal__actions">
              <button className="btn btn--primary" onClick={handleConfirmStep}>
                Confirm
              </button>
              <button className="btn" onClick={onClose}>Cancel</button>
            </div>
          </div>
        )}

        {step === "notes" && (
          <div className="modal__step">
            {topPoint && (
              <div className="modal__context">
                <span className="modal__context-label">Top talking point</span>
                <p>{topPoint}</p>
              </div>
            )}
            <h2 className="modal__title">What did you talk about?</h2>
            <textarea
              className="modal__textarea"
              placeholder="Quick notes… (optional but helps with the follow-up)"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={4}
              autoFocus
            />
            <div className="modal__actions">
              <button
                className="btn btn--primary"
                onClick={handleNotesNext}
                disabled={marking}
              >
                {marking ? "Saving…" : "Next"}
              </button>
              <button className="btn" onClick={async () => { await onMetMarked(notes); onClose(); }}>
                Save &amp; skip follow-up
              </button>
            </div>
          </div>
        )}

        {step === "channel" && (
          <div className="modal__step">
            <h2 className="modal__title">Send a follow-up via…</h2>
            <div className="channel-list">
              {availableChannels.map((c) => (
                <button
                  key={c.id}
                  className="btn btn--channel"
                  onClick={() => handleChannelSelect(c.id)}
                >
                  {c.label}
                </button>
              ))}
            </div>
            <button className="btn modal__skip" onClick={onClose}>
              Skip follow-up
            </button>
          </div>
        )}

        {step === "draft" && (
          <div className="modal__step">
            {drafting ? (
              <p className="modal__loading">Drafting your message…</p>
            ) : (
              <>
                <h2 className="modal__title">Review your message</h2>
                <textarea
                  className="modal__textarea modal__textarea--draft"
                  value={draftText}
                  onChange={(e) => setDraftText(e.target.value)}
                  rows={6}
                />
                {error && <p className="modal__error">{error}</p>}
                <div className="modal__actions">
                  <button
                    className="btn btn--primary"
                    onClick={handleSend}
                    disabled={sending || !draftText}
                  >
                    {sending ? "Sending…" : "Send"}
                  </button>
                  <button className="btn" onClick={onClose}>Save draft only</button>
                </div>
              </>
            )}
          </div>
        )}

        {step === "done" && (
          <div className="modal__step modal__step--done">
            <div className="modal__success">✓</div>
            <h2 className="modal__title">
              {channel ? "Sent!" : `${person.name} marked as met`}
            </h2>
            <button className="btn btn--primary" onClick={onClose}>Done</button>
          </div>
        )}
      </div>
    </div>
  );
}
