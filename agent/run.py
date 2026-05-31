#!/usr/bin/env python3
"""Event Intel agent CLI."""
import asyncio
import csv
import json
import logging
import sys
from pathlib import Path

# Ensure repo root is on sys.path so `import agent` works regardless of cwd
sys.path.insert(0, str(Path(__file__).parent.parent))

import click

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Event Intel — pre-event attendee research agent."""


# ---------------------------------------------------------------------------
# new-event
# ---------------------------------------------------------------------------

@cli.command("new-event")
@click.argument("event_name")
@click.option("--csv-file", "-f", type=click.Path(exists=True), help="CSV with columns: name,company,role,linkedin_url,twitter_handle,github_handle,instagram_handle")
def new_event(event_name: str, csv_file: str | None):
    """Register a new event and optionally bulk-import an attendee CSV."""
    attendees = []
    if csv_file:
        with open(csv_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                attendees.append({k.strip(): v.strip() for k, v in row.items()})
        click.echo(f"Loaded {len(attendees)} attendees from {csv_file}")

    if attendees:
        asyncio.run(_push_attendees(event_name, attendees))
    else:
        click.echo(f"Event '{event_name}' registered. Use --csv-file to import attendees.")


async def _push_attendees(event_name: str, attendees: list[dict]):
    from agent.sync.push_to_pi import push_raw_attendees

    result = await push_raw_attendees(event_name, attendees)
    if "error" in result:
        click.echo(f"Error from Pi: {result['error']}", err=True)
        sys.exit(1)
    click.echo(f"Pushed to Pi: {result.get('upserted', 0)} upserted")


# ---------------------------------------------------------------------------
# research (full event)
# ---------------------------------------------------------------------------

@cli.command("research")
@click.argument("event_name")
@click.option("--concurrency", "-n", default=3, show_default=True, help="Max parallel attendees")
@click.option("--dry-run", is_flag=True, help="Run recon but don't push to Pi")
def research(event_name: str, concurrency: int, dry_run: bool):
    """Research every unresearched attendee for an event (Step 2 after import-partiful).

    Runs LinkedIn, Twitter, GitHub, web search per person and pushes
    enriched profiles to the Pi. Use --concurrency to control speed vs rate-limit risk.
    """
    asyncio.run(_research_event(event_name, concurrency, dry_run))


async def _research_event(event_name: str, concurrency: int, dry_run: bool):
    from agent.config import settings
    import httpx

    url = settings.pi_url.rstrip("/") + f"/api/events"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, headers={"X-API-Secret": settings.pi_api_secret})
        if not resp.is_success:
            click.echo(f"Could not fetch events from Pi: {resp.status_code}", err=True)
            sys.exit(1)
        events = resp.json()

    event = next((e for e in events if e["name"].lower() == event_name.lower()), None)
    if not event:
        click.echo(f"Event '{event_name}' not found on Pi. Run new-event first.", err=True)
        sys.exit(1)

    event_id = event["id"]
    attendees_url = settings.pi_url.rstrip("/") + f"/api/events/{event_id}/people"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(attendees_url, headers={"X-API-Secret": settings.pi_api_secret})
        attendees = resp.json() if resp.is_success else []

    if not attendees:
        click.echo("No attendees found.")
        return

    click.echo(f"Researching {len(attendees)} attendees for '{event_name}'...")

    sem = asyncio.Semaphore(concurrency)

    async def research_one(att: dict):
        async with sem:
            await _research_person(att, event_name, dry_run)

    await asyncio.gather(*[research_one(a) for a in attendees])
    click.echo("Done.")


# ---------------------------------------------------------------------------
# research-one
# ---------------------------------------------------------------------------

@cli.command("research-one")
@click.argument("name")
@click.argument("company")
@click.option("--event", "-e", default="", help="Event name for context")
@click.option("--role", "-r", default="", help="Person's role/title")
@click.option("--linkedin", default=None)
@click.option("--twitter", default=None)
@click.option("--github", default=None)
@click.option("--instagram", default=None)
@click.option("--dry-run", is_flag=True, help="Print profile JSON, don't push to Pi")
@click.option("--output", "-o", type=click.Path(), default=None, help="Save JSON to file")
def research_one(name, company, event, role, linkedin, twitter, github, instagram, dry_run, output):
    """Run recon on a single person and optionally push to Pi."""
    asyncio.run(_research_single(
        name=name, company=company, event_name=event, role=role,
        linkedin_url=linkedin, twitter_handle=twitter,
        github_handle=github, instagram_handle=instagram,
        dry_run=dry_run, output_path=output,
    ))


async def _research_single(
    *, name, company, event_name, role,
    linkedin_url, twitter_handle, github_handle, instagram_handle,
    dry_run, output_path,
):
    from agent.recon.orchestrator import run_recon

    click.echo(f"Researching {name} @ {company}...")
    profile = await run_recon(
        name=name,
        company=company,
        role=role,
        event_name=event_name,
        linkedin_url=linkedin_url,
        twitter_handle=twitter_handle,
        github_handle=github_handle,
        instagram_handle=instagram_handle,
    )

    _print_profile(profile)

    if output_path:
        Path(output_path).write_text(json.dumps(profile, indent=2))
        click.echo(f"Saved to {output_path}")

    if not dry_run and event_name:
        from agent.sync.push_to_pi import push_profile
        ok = await push_profile(profile, event_name)
        if ok:
            click.echo("Pushed to Pi.")
        else:
            click.echo("Push failed — profile saved locally only.", err=True)


async def _research_person(att: dict, event_name: str, dry_run: bool):
    from agent.recon.orchestrator import run_recon
    from agent.sync.push_to_pi import push_profile

    person = att.get("person", att)
    name = person.get("name", "")
    company = person.get("company", "")
    if not name:
        return

    click.echo(f"  → {name} @ {company}")
    try:
        existing_recon = person.get("recon_sources") or {}
        profile = await run_recon(
            name=name,
            company=company,
            role=person.get("role", ""),
            event_name=event_name,
            linkedin_url=person.get("linkedin_url"),
            twitter_handle=person.get("twitter_handle"),
            github_handle=person.get("github_handle"),
            instagram_handle=person.get("instagram_handle"),
            existing_recon=existing_recon,
        )
        if not dry_run:
            await push_profile(profile, event_name)
        else:
            click.echo(json.dumps(profile, indent=2))
    except Exception as e:
        logger.error(f"Failed to research {name}: {e}")


# ---------------------------------------------------------------------------
# sync (re-push cached profiles)
# ---------------------------------------------------------------------------

@cli.command("sync")
@click.argument("json_file", type=click.Path(exists=True))
@click.argument("event_name")
def sync(json_file: str, event_name: str):
    """Push a previously saved profile JSON to Pi."""
    profile = json.loads(Path(json_file).read_text())
    asyncio.run(_do_sync(profile, event_name))


async def _do_sync(profile: dict, event_name: str):
    from agent.sync.push_to_pi import push_profile
    ok = await push_profile(profile, event_name)
    if ok:
        click.echo("Synced.")
    else:
        click.echo("Sync failed.", err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# import-partiful  (Step 1: scrape feed → import all events + guests to Pi)
# ---------------------------------------------------------------------------

@cli.command("import-partiful")
@click.option("--dry-run", is_flag=True, help="Print what would be imported, don't write to Pi")
def import_partiful(dry_run: bool):
    """Scrape your entire Partiful feed and import every event + guest list to the Pi.

    \b
    This is Step 1. It is fast — names only, no web research.
    Run `research <event-name>` afterwards when you want enriched profiles.
    """
    asyncio.run(_import_all_partiful(dry_run))


async def _import_all_partiful(dry_run: bool):
    from agent.recon.sources.partiful import scrape_all_my_events

    click.echo("Scraping your Partiful feed…")
    events = await scrape_all_my_events(names_only=True)

    if not events:
        click.echo("No events found. Make sure setup_partiful_auth.py has been run.")
        return

    click.echo(f"\nFound {len(events)} event(s):\n")

    for ev in events:
        name = ev.get("event_name") or "Unnamed Event"
        guests = ev.get("guests", [])
        date = ev.get("date", "")
        click.echo(f"  {name}{(' · ' + date) if date else ''}  — {len(guests)} guests")

        if dry_run:
            for g in guests[:5]:
                click.echo(f"      {g['name']}")
            if len(guests) > 5:
                click.echo(f"      … and {len(guests) - 5} more")
            continue

        from agent.sync.push_to_pi import push_raw_attendees
        raw = [
            {
                "name": g["name"],
                "instagram_handle": g.get("instagram"),
                "twitter_handle":   g.get("twitter"),
                "linkedin_url":     g.get("linkedin_url"),
            }
            for g in guests
        ]
        result = await push_raw_attendees(name, raw)
        if "error" in result:
            click.echo(f"    ✗ Push failed: {result['error']}", err=True)
        else:
            click.echo(f"    ✓ {result.get('upserted', len(guests))} upserted")

    if not dry_run:
        click.echo(
            "\nAll events imported. Run research when ready:\n"
            '  python3 agent/run.py research "<Event Name>"'
        )


# ---------------------------------------------------------------------------
# scrape-partiful  (single event URL — kept for manual use)
# ---------------------------------------------------------------------------

@cli.command("scrape-partiful")
@click.argument("partiful_url")
@click.option("--event", "-e", default=None, help="Override event name")
@click.option("--concurrency", "-n", default=2, show_default=True)
@click.option("--no-research", is_flag=True, help="Import names only, skip research")
@click.option("--dry-run", is_flag=True, help="Print guests, don't push or research")
def scrape_partiful(partiful_url: str, event: str | None, concurrency: int, no_research: bool, dry_run: bool):
    """Scrape a single Partiful event URL and optionally research everyone.

    For bulk import of all your events use `import-partiful` instead.
    """
    asyncio.run(_scrape_partiful(partiful_url, event, concurrency, no_research, dry_run))


async def _scrape_partiful(url: str, event_name_override: str | None, concurrency: int, no_research: bool, dry_run: bool):
    from agent.recon.sources.partiful import scrape_partiful_event

    click.echo(f"Scraping Partiful event: {url}")
    result = await scrape_partiful_event(url, names_only=dry_run)

    if not result:
        click.echo("ERROR: Could not scrape Partiful event. Make sure you've run setup_partiful_auth.py.", err=True)
        sys.exit(1)

    event_name = event_name_override or result.get("event_name") or "Unnamed Event"
    guests = result.get("guests", [])

    if not guests:
        click.echo("No guests found on this event page.")
        return

    click.echo(f"\nEvent: {event_name}")
    if result.get("date"):
        click.echo(f"Date:  {result['date']}")
    if result.get("location"):
        click.echo(f"Location: {result['location']}")
    click.echo(f"Guests: {len(guests)}\n")

    if dry_run:
        for g in guests:
            handles = _format_handles(g)
            click.echo(f"  {g['name']}{(' — ' + handles) if handles else ''}")
        return

    # Push raw attendees to Pi first (they appear in the app immediately)
    raw = []
    for g in guests:
        raw.append({
            "name": g["name"],
            "instagram_handle": g.get("instagram"),
            "twitter_handle": g.get("twitter"),
            "linkedin_url": g.get("linkedin_url"),
        })

    from agent.sync.push_to_pi import push_raw_attendees
    push_result = await push_raw_attendees(event_name, raw)
    if "error" in push_result:
        click.echo(f"Warning: Pi push returned: {push_result['error']}", err=True)
    else:
        click.echo(f"Pushed {push_result.get('upserted', len(guests))} attendees to Pi.")

    if no_research:
        click.echo("Skipping research (--no-research).")
        return

    # Research each guest
    click.echo(f"\nResearching {len(guests)} guests (concurrency={concurrency})...")
    sem = asyncio.Semaphore(concurrency)

    async def research_guest(g: dict):
        async with sem:
            await _research_partiful_guest(g, event_name)

    await asyncio.gather(*[research_guest(g) for g in guests])
    click.echo("\nDone. Open the app to see enriched profiles.")


async def _research_partiful_guest(guest: dict, event_name: str):
    """Research a single Partiful guest and push the enriched profile."""
    from agent.recon.orchestrator import run_recon
    from agent.sync.push_to_pi import push_profile

    name = guest["name"]
    instagram = guest.get("instagram")
    twitter = guest.get("twitter")
    linkedin_url = guest.get("linkedin_url")

    has_handles = any([instagram, twitter, linkedin_url])
    click.echo(f"  → {name}{' [' + _format_handles(guest) + ']' if has_handles else ' [LinkedIn search]'}")

    try:
        profile = await run_recon(
            name=name,
            company="",
            role="",
            event_name=event_name,
            linkedin_url=linkedin_url,
            twitter_handle=twitter,
            github_handle=None,
            instagram_handle=instagram,
        )
        await push_profile(profile, event_name)
    except Exception as e:
        logger.error(f"Research failed for {name}: {e}")


def _format_handles(g: dict) -> str:
    parts = []
    if g.get("instagram"):
        parts.append(f"ig:{g['instagram']}")
    if g.get("twitter"):
        parts.append(f"tw:{g['twitter']}")
    if g.get("linkedin_url"):
        parts.append("li:✓")
    return ", ".join(parts)


# ---------------------------------------------------------------------------
# identify (Phase 15 stub)
# ---------------------------------------------------------------------------

@cli.command("identify")
@click.argument("image_path", type=click.Path(exists=True))
@click.option("--event", "-e", required=True, help="Event name to search attendees")
def identify(image_path: str, event: str):
    """Identify a person from a photo against event attendees (Phase 15 stub)."""
    click.echo("Face identification not yet implemented (Phase 15).")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _print_profile(profile: dict):
    click.echo(f"\n{'='*60}")
    click.echo(f"  {profile.get('name')} @ {profile.get('company')}")
    click.echo(f"{'='*60}")
    click.echo(f"\nSummary: {profile.get('background_summary', 'N/A')}")
    click.echo("\nTalking points:")
    for tp in profile.get("talking_points", []):
        click.echo(f"  • {tp}")
    hook = profile.get("outreach_hook")
    if hook:
        click.echo(f"\nOutreach hook: {hook}")
    caution = profile.get("caution")
    if caution:
        click.echo(f"\nCaution: {caution}")
    click.echo()


if __name__ == "__main__":
    cli()
