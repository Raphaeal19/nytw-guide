import type { AttendancePerson } from "../types";

interface Props {
  person: AttendancePerson;
}

export function TalkingPoints({ person }: Props) {
  const points = [...(person.talking_points ?? [])].sort(
    (a, b) => a.priority - b.priority
  );

  return (
    <div className="section">
      {person.bio_snapshot && (
        <div className="section__block">
          <h3 className="section__label">Bio</h3>
          <p className="section__text">{person.bio_snapshot}</p>
        </div>
      )}

      {points.length > 0 && (
        <div className="section__block">
          <h3 className="section__label">Talking points</h3>
          <ol className="talking-points">
            {points.map((tp, i) => (
              <li key={i} className="talking-point">
                <p className="talking-point__text">{tp.text}</p>
                <span className="talking-point__source">{tp.source}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {person.open_roles && person.open_roles.length > 0 && (
        <div className="section__block">
          <h3 className="section__label">Open roles</h3>
          <div className="open-roles">
            {person.open_roles.map((r, i) => (
              <div key={i} className="open-role">
                <p className="open-role__title">
                  {r.url ? (
                    <a href={r.url} target="_blank" rel="noopener noreferrer">
                      {r.title}
                    </a>
                  ) : (
                    r.title
                  )}
                </p>
                <p className="open-role__meta">
                  {[r.dept, r.location].filter(Boolean).join(" · ")}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {!person.bio_snapshot && points.length === 0 && (
        <p className="empty-state">No intel yet — run the agent pipeline to populate this profile.</p>
      )}
    </div>
  );
}
