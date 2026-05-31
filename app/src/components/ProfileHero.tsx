import type { AttendancePerson } from "../types";

interface Props {
  person: AttendancePerson;
  onMetToggle: () => void;
}

function initials(name: string) {
  return name.split(" ").slice(0, 2).map((w) => w[0]).join("").toUpperCase();
}

function nameColor(name: string) {
  const colors = ["#7F77DD", "#DD7777", "#77DDBB", "#DDC277", "#77AADD", "#DD77AA"];
  let h = 0;
  for (const c of name) h = (h * 31 + c.charCodeAt(0)) & 0xffffffff;
  return colors[Math.abs(h) % colors.length];
}

export function ProfileHero({ person, onMetToggle }: Props) {
  const links = [
    { label: "LinkedIn", url: person.linkedin_url },
    { label: "𝕏", url: person.twitter_handle ? `https://twitter.com/${person.twitter_handle}` : null },
    { label: "GitHub", url: person.github_handle ? `https://github.com/${person.github_handle}` : null },
  ].filter((l) => l.url);

  return (
    <div className="profile-hero">
      <div className="profile-hero__avatar-wrap">
        {person.photo_url ? (
          <img className="profile-hero__avatar" src={person.photo_url} alt={person.name} />
        ) : (
          <div
            className="profile-hero__avatar profile-hero__avatar--initials"
            style={{ background: nameColor(person.name) }}
          >
            {initials(person.name)}
          </div>
        )}
      </div>
      <div className="profile-hero__info">
        <h1 className="profile-hero__name">{person.name}</h1>
        {(person.role || person.company) && (
          <p className="profile-hero__sub">
            {[person.role, person.company].filter(Boolean).join(" · ")}
          </p>
        )}
        {person.location && (
          <p className="profile-hero__location">📍 {person.location}</p>
        )}
        {links.length > 0 && (
          <div className="profile-hero__links">
            {links.map((l) => (
              <a
                key={l.label}
                href={l.url!}
                target="_blank"
                rel="noopener noreferrer"
                className="social-pill"
                onClick={(e) => e.stopPropagation()}
              >
                {l.label}
              </a>
            ))}
          </div>
        )}
      </div>
      <button
        className={`met-toggle ${person.met ? "met-toggle--active" : ""}`}
        onClick={onMetToggle}
      >
        {person.met ? "✓ Met" : "Mark as met"}
      </button>
    </div>
  );
}
