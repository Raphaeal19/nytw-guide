"""Push a synthesized PersonProfile to the Pi's /api/ingest endpoint."""
from __future__ import annotations

import logging

import httpx

from agent.config import settings

logger = logging.getLogger(__name__)


async def get_or_create_event(event_name: str) -> str | None:
    """Return event UUID string, creating the event if it doesn't exist."""
    base = settings.pi_url.rstrip("/")
    headers = {"X-Ingest-Secret": settings.pi_api_secret}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{base}/api/events", headers=headers)
            if resp.is_success:
                for ev in resp.json():
                    if ev.get("name", "").lower() == event_name.lower():
                        return ev["id"]

            # Not found — create it
            resp = await client.post(
                f"{base}/api/events",
                json={"name": event_name},
                headers=headers,
            )
            if resp.is_success:
                return resp.json()["id"]

    except Exception as e:
        logger.error(f"Could not get/create event '{event_name}': {e}")

    return None


async def push_profile(profile: dict, event_name: str) -> bool:
    event_id = await get_or_create_event(event_name)
    if not event_id:
        logger.error(f"Could not resolve event_id for '{event_name}'")
        return False

    payload = _build_ingest_payload(event_id, profile)
    url = settings.pi_url.rstrip("/") + "/api/ingest"
    headers = {"X-Ingest-Secret": settings.pi_api_secret}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.is_success:
                logger.info(f"Pushed {profile['name']} → Pi ({resp.json()})")
                return True
            logger.warning(f"Pi rejected {profile['name']}: {resp.status_code} {resp.text[:200]}")
            return False
    except Exception as e:
        logger.error(f"Failed to push {profile['name']} to Pi: {e}")
        return False


async def push_raw_attendees(event_name: str, attendees: list[dict]) -> dict:
    """Push a list of raw attendee dicts (from CSV) without recon."""
    event_id = await get_or_create_event(event_name)
    if not event_id:
        return {"error": f"Could not resolve event_id for '{event_name}'"}

    people = []
    for att in attendees:
        people.append({
            "name": att.get("name", ""),
            "company": att.get("company"),
            "role": att.get("role"),
            "linkedin_url": att.get("linkedin_url"),
            "twitter_handle": att.get("twitter_handle"),
            "github_handle": att.get("github_handle"),
            "instagram_handle": att.get("instagram_handle"),
        })

    payload = {"event_id": event_id, "people": people}
    url = settings.pi_url.rstrip("/") + "/api/ingest"
    headers = {"X-Ingest-Secret": settings.pi_api_secret}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.is_success:
                return resp.json()
            return {"error": f"{resp.status_code} {resp.text[:200]}"}
    except Exception as e:
        return {"error": str(e)}


def _build_ingest_payload(event_id: str, profile: dict) -> dict:
    talking_points = []
    for i, tp in enumerate(profile.get("talking_points", [])):
        if isinstance(tp, str):
            talking_points.append({"text": tp, "source": "agent", "priority": i + 1})
        elif isinstance(tp, dict):
            talking_points.append(tp)

    hook = profile.get("outreach_hook", "")
    if hook:
        talking_points.append({"text": hook, "source": "outreach_hook", "priority": len(talking_points) + 1})

    recon = profile.get("recon_sources", {})

    open_roles: list[dict] = []
    company_data = recon.get("company", {}).get("data", {})
    for role in company_data.get("open_roles", []):
        open_roles.append({
            "title": role.get("title", ""),
            "url": role.get("url"),
        })

    person: dict = {
        "name": profile["name"],
        "company": profile.get("company"),
        "role": profile.get("role"),
        "linkedin_url": profile.get("linkedin_url"),
        "twitter_handle": profile.get("twitter_handle"),
        "github_handle": profile.get("github_handle"),
        "instagram_handle": profile.get("instagram_handle"),
        "bio_snapshot": profile.get("background_summary"),
        "talking_points": talking_points or None,
        "recon_sources": recon or None,
        "open_roles": open_roles or None,
    }

    return {"event_id": event_id, "people": [person]}
