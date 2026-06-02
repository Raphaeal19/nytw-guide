import { useNavigate } from "react-router-dom";
import type { AttendancePerson } from "../types";

interface Props {
  match: AttendancePerson | null;
  confidence: number;
  eventId: string;
  error?: string;
  onRetry: () => void;
  onClose: () => void;
}

export function IdentifyResult({
  match,
  confidence,
  eventId,
  error,
  onRetry,
  onClose,
}: Props) {
  const navigate = useNavigate();

  if (error) {
    return (
      <div className="camera-overlay">
        <div className="identify-result">
          <p className="identify-result__msg">{error}</p>
          <div className="identify-result__actions">
            <button className="btn btn--primary" onClick={onRetry}>
              Try Again
            </button>
            <button className="btn" onClick={onClose}>
              Close
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!match) {
    return (
      <div className="camera-overlay">
        <div className="identify-result">
          <div className="identify-result__icon">?</div>
          <h2 className="identify-result__title">No Match Found</h2>
          <p className="identify-result__msg">
            Couldn't match this face to any attendee.
          </p>
          <div className="identify-result__actions">
            <button className="btn btn--primary" onClick={onRetry}>
              Try Again
            </button>
            <button className="btn" onClick={onClose}>
              Close
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="camera-overlay">
      <div className="identify-result">
        <div className="identify-result__card">
          {match.photo_url ? (
            <img
              className="identify-result__avatar"
              src={match.photo_url}
              alt={match.name}
            />
          ) : (
            <div className="identify-result__avatar identify-result__avatar--initials">
              {match.name.charAt(0)}
            </div>
          )}
          <h2 className="identify-result__name">{match.name}</h2>
          <p className="identify-result__sub">
            {[match.role, match.company].filter(Boolean).join(" at ")}
          </p>
          <span className="identify-result__confidence">
            {Math.round(confidence * 100)}% match
          </span>
        </div>

        {match.talking_points && match.talking_points.length > 0 && (
          <div className="identify-result__points">
            <span className="identify-result__points-label">Talking points</span>
            <ul>
              {match.talking_points
                .slice()
                .sort((a, b) => a.priority - b.priority)
                .slice(0, 3)
                .map((tp, i) => (
                  <li key={i}>{tp.text}</li>
                ))}
            </ul>
          </div>
        )}

        <div className="identify-result__actions">
          <button
            className="btn btn--primary btn--full"
            onClick={() =>
              navigate(`/events/${eventId}/people/${match.person_id}`)
            }
          >
            View Full Profile
          </button>
          <button className="btn btn--full" onClick={onRetry}>
            Scan Another
          </button>
        </div>
      </div>
    </div>
  );
}
