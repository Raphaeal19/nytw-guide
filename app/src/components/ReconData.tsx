import { useState } from "react";
import type { AttendancePerson, ReconSource } from "../types";

interface Props {
  person: AttendancePerson;
}

interface SourceConfig {
  label: string;
  icon: string;
  color: string;
  countLabel: (n: number) => string;
  profileUrl?: (person: AttendancePerson) => string | null;
}

const SOURCE_CONFIG: Record<string, SourceConfig> = {
  linkedin: {
    label: "LinkedIn",
    icon: "in",
    color: "#0a66c2",
    countLabel: (n) => `${n} post${n !== 1 ? "s" : ""}`,
    profileUrl: (p) => p.linkedin_url,
  },
  twitter: {
    label: "Twitter / X",
    icon: "𝕏",
    color: "#000",
    countLabel: (n) => `${n} post${n !== 1 ? "s" : ""}`,
    profileUrl: (p) => p.twitter_handle ? `https://x.com/${p.twitter_handle}` : null,
  },
  github: {
    label: "GitHub",
    icon: "GH",
    color: "#24292f",
    countLabel: (n) => `${n} repo${n !== 1 ? "s" : ""}`,
    profileUrl: (p) => p.github_handle ? `https://github.com/${p.github_handle}` : null,
  },
  reddit: {
    label: "Reddit",
    icon: "r/",
    color: "#ff4500",
    countLabel: (n) => `${n} post${n !== 1 ? "s" : ""}`,
  },
  instagram: {
    label: "Instagram",
    icon: "ig",
    color: "#e1306c",
    countLabel: (n) => `${n} post${n !== 1 ? "s" : ""}`,
  },
  company: {
    label: "Company page",
    icon: "co",
    color: "#555",
    countLabel: () => "",
  },
  web: {
    label: "Web search",
    icon: "🌐",
    color: "#1a73e8",
    countLabel: () => "",
  },
};

function hasData(source: ReconSource): boolean {
  const count = source.posts_found ?? source.repos_found ?? 0;
  return count > 0 || (source.summary?.trim().length ?? 0) > 0;
}

function SourceRow({
  sourceKey,
  source,
  person,
}: {
  sourceKey: string;
  source: ReconSource;
  person: AttendancePerson;
}) {
  const [open, setOpen] = useState(false);
  const cfg = SOURCE_CONFIG[sourceKey] ?? {
    label: sourceKey,
    icon: sourceKey.slice(0, 2),
    color: "#888",
    countLabel: (n: number) => `${n} items`,
  };

  const count = source.posts_found ?? source.repos_found ?? null;
  const active = hasData(source);
  const profileUrl = cfg.profileUrl?.(person) ?? null;

  return (
    <div className={`recon-row ${open ? "recon-row--open" : ""} ${!active ? "recon-row--empty" : ""}`}>
      <button className="recon-row__header" onClick={() => setOpen((o) => !o)}>
        <span
          className="recon-icon"
          style={{ background: active ? cfg.color : "#e5e5e5", color: active ? "#fff" : "#999" }}
        >
          {cfg.icon}
        </span>
        <span className="recon-row__label">{cfg.label}</span>
        <span className="recon-row__meta">
          {active
            ? count !== null
              ? cfg.countLabel(count)
              : "data found"
            : "no data"}
        </span>
        <span className="recon-row__chevron">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="recon-row__body">
          {count !== null && count > 0 && (
            <p className="recon-detail-count">
              {cfg.countLabel(count)} found
            </p>
          )}
          {source.summary?.trim() ? (
            <p className="recon-detail-summary">{source.summary}</p>
          ) : (
            <p className="recon-detail-summary recon-detail-summary--empty">
              {active ? "No summary available." : "Nothing found on this source."}
            </p>
          )}
          {profileUrl && (
            <a
              href={profileUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="recon-detail-link"
            >
              View profile →
            </a>
          )}
        </div>
      )}
    </div>
  );
}

export function ReconData({ person }: Props) {
  const sources = person.recon_sources ?? {};
  const allKeys = Object.keys(SOURCE_CONFIG);
  const presentKeys = allKeys.filter((k) => k in sources);

  const activeCount = presentKeys.filter((k) => hasData(sources[k]!)).length;

  if (presentKeys.length === 0) {
    return (
      <div className="section">
        <p className="empty-state">
          No source data yet. Run the agent pipeline to populate this profile.
        </p>
      </div>
    );
  }

  return (
    <div className="section">
      <div className="section__block">
        <p className="recon-summary-line">
          Found data on{" "}
          <strong>{activeCount} of {presentKeys.length}</strong>{" "}
          source{presentKeys.length !== 1 ? "s" : ""} checked.{" "}
          {person.agent_ran_at && (
            <span className="recon-ran-at">
              Last scraped{" "}
              {new Date(person.agent_ran_at).toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
                year: "numeric",
              })}
              .
            </span>
          )}
        </p>
      </div>

      <div className="recon-list">
        {/* Active sources first */}
        {presentKeys
          .filter((k) => hasData(sources[k]!))
          .map((k) => (
            <SourceRow key={k} sourceKey={k} source={sources[k]!} person={person} />
          ))}
        {/* Empty sources at bottom */}
        {presentKeys
          .filter((k) => !hasData(sources[k]!))
          .map((k) => (
            <SourceRow key={k} sourceKey={k} source={sources[k]!} person={person} />
          ))}
      </div>
    </div>
  );
}
