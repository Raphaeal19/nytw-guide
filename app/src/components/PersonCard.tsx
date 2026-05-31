import { useNavigate } from "react-router-dom";
import type { AttendancePerson } from "../types";

interface Props {
  person: AttendancePerson;
  eventId: string;
  onMetToggle: (p: AttendancePerson) => void;
}

function initials(name: string) {
  return name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
}

function nameColor(name: string) {
  const colors = ["#7F77DD", "#DD7777", "#77DDBB", "#DDC277", "#77AADD", "#DD77AA"];
  let h = 0;
  for (const c of name) h = (h * 31 + c.charCodeAt(0)) & 0xffffffff;
  return colors[Math.abs(h) % colors.length];
}

function activeSources(recon: AttendancePerson["recon_sources"]): string[] {
  if (!recon) return [];
  return Object.entries(recon)
    .filter(([, v]) => v && ((v.posts_found ?? v.repos_found ?? 0) > 0 || v.summary))
    .map(([k]) => k);
}

const SOURCE_ICONS: Record<string, string> = {
  linkedin: "in",
  twitter: "𝕏",
  github: "gh",
  reddit: "r/",
  instagram: "ig",
  company: "co",
  web: "🌐",
};

export function PersonCard({ person, eventId, onMetToggle }: Props) {
  const navigate = useNavigate();
  const topPoint = person.talking_points
    ?.sort((a, b) => a.priority - b.priority)[0]?.text;

  return (
    <div
      className={`person-card ${person.met ? "person-card--met" : ""}`}
      onClick={() =>
        navigate(
          `/events/${eventId}/people/${person.person_id}?attendanceId=${person.attendance_id}`
        )
      }
    >
      <div className="person-card__avatar-wrap">
        {person.photo_url ? (
          <img
            className="person-card__avatar"
            src={person.photo_url}
            alt={person.name}
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = "none";
            }}
          />
        ) : (
          <div
            className="person-card__avatar person-card__avatar--initials"
            style={{ background: nameColor(person.name) }}
          >
            {initials(person.name)}
          </div>
        )}
        {person.met && <span className="person-card__met-badge">✓</span>}
      </div>

      <div className="person-card__body">
        <p className="person-card__name">{person.name}</p>
        <p className="person-card__sub">
          {[person.role, person.company].filter(Boolean).join(" · ")}
        </p>
        {topPoint && (
          <p className="person-card__hook">{topPoint}</p>
        )}
        {activeSources(person.recon_sources).length > 0 && (
          <div className="person-card__sources">
            {activeSources(person.recon_sources).map((s) => (
              <span key={s} className="source-chip">{SOURCE_ICONS[s] ?? s}</span>
            ))}
          </div>
        )}
      </div>

      <button
        className={`met-btn ${person.met ? "met-btn--active" : ""}`}
        onClick={(e) => {
          e.stopPropagation();
          onMetToggle(person);
        }}
        aria-label={person.met ? "Mark as not met" : "Mark as met"}
      >
        {person.met ? "✓" : "○"}
      </button>
    </div>
  );
}
