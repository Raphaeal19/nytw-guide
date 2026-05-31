"""Assembles the final PersonProfile JSON from raw recon + synthesized insights."""
from __future__ import annotations

import datetime
from datetime import timezone
from typing import Any


def build_person_profile(
    *,
    name: str,
    company: str,
    role: str,
    event_name: str,
    raw_sources: dict[str, Any],
    synthesis: dict[str, Any],
) -> dict[str, Any]:
    handles = _extract_handles(raw_sources)

    recon_sources: dict[str, Any] = {}
    for src, data in raw_sources.items():
        if data:
            recon_sources[src] = {
                "scraped_at": datetime.datetime.now(timezone.utc).isoformat(),
                "data": data,
                "summary": data.get("summary") or data.get("summary_text") or "",
            }

    return {
        "name": name,
        "company": company,
        "role": role,
        "event": event_name,
        "linkedin_url": handles.get("linkedin_url"),
        "twitter_handle": handles.get("twitter_handle"),
        "github_handle": handles.get("github_handle"),
        "instagram_handle": handles.get("instagram_handle"),
        "talking_points": synthesis.get("talking_points", []),
        "background_summary": synthesis.get("background_summary", ""),
        "shared_interests": synthesis.get("shared_interests", []),
        "outreach_hook": synthesis.get("outreach_hook", ""),
        "caution": synthesis.get("caution", ""),
        "recon_sources": recon_sources,
        "agent_version": "phase4",
    }


def _extract_handles(sources: dict[str, Any]) -> dict[str, str | None]:
    handles: dict[str, str | None] = {
        "linkedin_url": None,
        "twitter_handle": None,
        "github_handle": None,
        "instagram_handle": None,
    }

    web = sources.get("web", {})
    if web:
        handles["linkedin_url"] = web.get("linkedin_url")
        handles["twitter_handle"] = web.get("twitter_handle")
        handles["github_handle"] = web.get("github_handle")

    li = sources.get("linkedin", {})
    if li and li.get("profile_url"):
        handles["linkedin_url"] = li["profile_url"]

    gh = sources.get("github", {})
    if gh and gh.get("handle"):
        handles["github_handle"] = gh["handle"]

    tw = sources.get("twitter", {})
    if tw and tw.get("handle"):
        handles["twitter_handle"] = tw["handle"]

    ig = sources.get("instagram", {})
    if ig and ig.get("handle"):
        handles["instagram_handle"] = ig["handle"]

    return handles
