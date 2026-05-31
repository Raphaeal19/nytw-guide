# Event Intel — Complete Build Spec
> Hand this file to Claude Code as-is.
> Start with: "Scaffold this project exactly as described. Follow the build order at the bottom."

---

## What this is

A personal event networking tool. Before an event, a Mac-side agent pipeline researches every
attendee and produces rich profiles — talking points, bio, open roles, conversation hooks. At the
event, you browse profiles on your phone via a PWA served from a Raspberry Pi. After meeting
someone, you flip a "met" toggle, add a quick note, and the Pi drafts and sends a personalized
follow-up message through LinkedIn, email, or Twitter.

Designed to handle ~1000 people across multiple events, with many repeat attendees. People are
researched once globally and reused across events — only per-event state (met, notes, outreach)
is stored separately.

---

## Hardware split

| Machine | Role |
|---|---|
| MacBook M4 Pro (24GB RAM) | One-time pre-event agent pipeline: scraping, face matching, LLM synthesis |
| Raspberry Pi (always on) | App server: FastAPI, Postgres, Redis, small-model drafting, outreach sending |
| iPhone (browser) | PWA client used at the event |

---

## Repo structure

```
event-intel/
├── agent/                              # Runs on MacBook only — never deployed to Pi
│   ├── recon/
│   │   ├── orchestrator.py             # LangGraph graph + incremental batch runner
│   │   └── sources/
│   │       ├── linkedin.py             # open-linkedin-api, account rotation, 15s+ delays
│   │       ├── twitter.py              # Playwright, public timelines
│   │       ├── reddit.py               # PRAW (official Reddit API, free)
│   │       ├── github.py               # GitHub REST API, unauthenticated
│   │       ├── instagram.py            # instaloader, public profiles only
│   │       ├── company.py              # Playwright — about page + careers/jobs page
│   │       └── web.py                  # Serper API for Google search
│   ├── face_match/
│   │   ├── matcher.py                  # DeepFace + ArcFace, fully local
│   │   └── resolver.py                 # photo → confirmed identity
│   ├── synthesizer/
│   │   ├── synthesizer.py              # Routes to Ollama (qwen2.5:32b) or Anthropic API
│   │   ├── prompts.py                  # Synthesis prompt + structured output schema
│   │   └── document_agent.py           # Assembles final PersonProfile JSON
│   ├── sync/
│   │   └── push_to_pi.py               # HTTP POST to Pi /api/ingest
│   ├── setup_linkedin_auth.py          # One-time: saves LinkedIn cookie state for Playwright
│   ├── config.py                       # All env vars, model config, Pi URL
│   └── run.py                          # CLI entrypoint (see CLI section)
│
├── server/                             # Runs on Raspberry Pi
│   ├── api/
│   │   ├── main.py                     # FastAPI app, CORS, lifespan
│   │   ├── routes/
│   │   │   ├── events.py               # CRUD for events
│   │   │   ├── people.py               # CRUD for people + attendance
│   │   │   ├── ingest.py               # POST /api/ingest — receives profiles from Mac
│   │   │   ├── met.py                  # POST /api/attendance/{id}/met
│   │   │   └── outreach.py             # POST /api/outreach/draft and /send
│   │   └── deps.py                     # DB session dependency, ingest auth
│   ├── db/
│   │   ├── models.py                   # SQLAlchemy models (3-table schema)
│   │   ├── database.py                 # Engine + session factory
│   │   └── migrations/                 # Alembic — run: alembic upgrade head
│   ├── drafter/
│   │   ├── drafter.py                  # Calls Ollama on Pi (phi3.5:3.8b)
│   │   └── prompts.py                  # Message drafting prompt
│   ├── outreach/
│   │   ├── linkedin.py                 # Playwright DM sender
│   │   ├── gmail.py                    # Gmail SMTP + app password
│   │   └── twitter.py                  # Twitter API v2 DM sender
│   ├── tasks/
│   │   ├── celery_app.py               # Celery + Redis config
│   │   └── send_task.py                # Async send with retries
│   └── config.py                       # Env vars from server/.env
│
└── app/                                # React PWA — built and served as static files by Pi
    ├── public/
    │   └── manifest.json               # PWA manifest
    ├── src/
    │   ├── pages/
    │   │   ├── EventDetail.tsx          # Per-event attendee grid — main at-event view
    │   │   └── PersonProfile.tsx        # Full profile detail page
    │   ├── components/
    │   │   ├── EventTabs.tsx            # Top tab bar: one tab per event + add button
    │   │   ├── EventHeader.tsx          # Event title, date, location, tags, stats bar
    │   │   ├── PersonCard.tsx           # Card: avatar, hook, met toggle
    │   │   ├── MetModal.tsx             # confirm → notes → channel → draft → send
    │   │   ├── ProfileHero.tsx          # Large header on profile page
    │   │   ├── TalkingPoints.tsx        # Ranked hooks with source citations
    │   │   ├── ReconData.tsx            # Per-source breakdown tab
    │   │   └── OutreachPanel.tsx        # Draft + edit + send panel
    │   ├── hooks/
    │   │   ├── useEvents.ts
    │   │   ├── usePeople.ts
    │   │   └── useOutreach.ts
    │   ├── api/
    │   │   └── client.ts               # Axios instance → pi.local:8000
    │   ├── sw.ts                        # Service worker — offline cache
    │   └── main.tsx
    ├── vite.config.ts                   # Include vite-plugin-pwa
    └── package.json
```

---

## Database schema — 3 tables

The key architectural decision for scale: `Person` is global (scraped once, reused across events).
`EventAttendance` is the join table holding all per-event state. `Event` is unchanged.

```python
# server/db/models.py

from sqlalchemy import (Column, String, Boolean, Text, Date, DateTime,
                        ForeignKey, Integer, UniqueConstraint)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from uuid import uuid4
from datetime import datetime
from .database import Base


class Event(Base):
    __tablename__ = "events"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name        = Column(String, nullable=False)       # "SaaStr Annual 2025"
    date_start  = Column(Date)
    date_end    = Column(Date)
    location    = Column(String)
    description = Column(Text)
    tags        = Column(ARRAY(String))                # ["SaaS", "B2B", "Founders"]
    color       = Column(String)                       # hex for tab dot in UI
    created_at  = Column(DateTime, default=datetime.utcnow)

    attendances = relationship("EventAttendance", back_populates="event",
                               cascade="all, delete")


class Person(Base):
    """
    Global person record. Created once, reused across all events.
    Scraped data lives here. Per-event state lives in EventAttendance.
    """
    __tablename__ = "people"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # --- Identity ---
    name             = Column(String, nullable=False)
    company          = Column(String)
    role             = Column(String)
    location         = Column(String)
    photo_url        = Column(String)           # resolved from face match or CSV

    # --- Social links (all optional) ---
    linkedin_url     = Column(String)
    twitter_handle   = Column(String)
    github_handle    = Column(String)
    instagram_handle = Column(String)
    personal_site    = Column(String)
    email            = Column(String)

    # --- Agent output (global, not per-event) ---
    bio_snapshot     = Column(Text)             # 3-4 sentence career summary
    talking_points   = Column(JSONB)            # [{text, source, priority}, ...]
    recon_sources    = Column(JSONB)            # {linkedin: {posts_found, summary}, ...}
    raw_intel        = Column(JSONB)            # full scraped blob, for debugging
    agent_ran_at     = Column(DateTime)         # when scrape + synthesis last ran

    created_at       = Column(DateTime, default=datetime.utcnow)

    attendances = relationship("EventAttendance", back_populates="person")


class EventAttendance(Base):
    """
    Join table: one row per (person, event) pair.
    Holds everything that is specific to one event appearance:
    open roles (time-sensitive), met state, outreach.
    """
    __tablename__ = "event_attendances"

    # Unique constraint: a person can only appear once per event
    __table_args__ = (
        UniqueConstraint("person_id", "event_id", name="uq_person_event"),
    )

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    person_id = Column(UUID(as_uuid=True), ForeignKey("people.id"), nullable=False)
    event_id  = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)

    # --- Open roles scraped at time of this event (time-sensitive, always re-scraped) ---
    open_roles = Column(JSONB)              # [{title, dept, location, url}, ...]

    # --- Met state ---
    met        = Column(Boolean, default=False)
    met_at     = Column(DateTime)
    met_notes  = Column(Text)              # quick notes typed right after meeting them

    # --- Outreach ---
    outreach_sent    = Column(Boolean, default=False)
    outreach_channel = Column(String)      # "linkedin" | "email" | "twitter"
    outreach_draft   = Column(Text)
    outreach_sent_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)

    person = relationship("Person", back_populates="attendances")
    event  = relationship("Event",  back_populates="attendances")
```

---

## Agent pipeline — incremental batch runner

### The deduplication + freshness logic

Every person in the CSV goes through this decision tree before any scraping happens:

```python
# agent/recon/orchestrator.py

FRESH_DAYS     = 90   # full profile considered current within 90 days
ROLE_FRESH_DAYS = 30  # open roles always re-scraped if older than 30 days

async def process_person(input: PersonInput, event_id: UUID, db_client: DBClient):
    """
    Single-person pipeline. Called once per row in the CSV.
    Writes to DB immediately on success — batch is resumable after any crash.
    """
    existing = await db_client.find_person(name=input.name, company=input.company)

    if existing:
        # Check if attendance record already exists for this event
        # (means this person was already processed in a previous run / resume)
        already_done = await db_client.find_attendance(
            person_id=existing.id, event_id=event_id
        )
        if already_done:
            logger.info(f"SKIP  {input.name} — already processed for this event")
            return

        if is_fresh(existing.agent_ran_at, max_age_days=FRESH_DAYS):
            # Profile is current — skip full scrape, only re-scrape open roles
            logger.info(f"ROLES {input.name} — profile fresh, refreshing open roles only")
            open_roles = await scrape_company_jobs(existing.company)
            await db_client.create_attendance(
                person_id=existing.id,
                event_id=event_id,
                open_roles=open_roles
            )
            return

        else:
            # Profile is stale — run full pipeline and update
            logger.info(f"REFRESH {input.name} — profile stale, re-scraping")
            profile = await run_full_pipeline(input, existing_identity=existing)
            await db_client.update_person(existing.id, profile)
            await db_client.create_attendance(
                person_id=existing.id,
                event_id=event_id,
                open_roles=profile.open_roles
            )

    else:
        # Brand new person — full scrape + synthesis
        logger.info(f"NEW   {input.name} — running full pipeline")
        profile = await run_full_pipeline(input)
        person  = await db_client.create_person(profile)
        await db_client.create_attendance(
            person_id=person.id,
            event_id=event_id,
            open_roles=profile.open_roles
        )


async def run_batch(csv_rows: list[PersonInput], event_id: UUID, db_client: DBClient,
                    concurrency: int = 5):
    """
    Processes all people in the CSV with bounded concurrency.
    Each person is written to DB immediately on success.
    Failures are logged and skipped — they can be retried on resume.
    """
    semaphore = asyncio.Semaphore(concurrency)

    async def process_with_guard(person: PersonInput):
        async with semaphore:
            try:
                await process_person(person, event_id, db_client)
            except Exception as e:
                logger.error(f"FAIL  {person.name}: {e}")
                # Do not re-raise — continue with next person

    await asyncio.gather(*[process_with_guard(p) for p in csv_rows])
```

### Resume behavior

Because every successful person is written immediately to the DB, a crash mid-run is harmless.
On restart, `run.py research --resume` re-reads the CSV, checks which people already have an
attendance record for this event, and skips them. The batch picks up exactly where it left off.

```python
# run.py — research subcommand

@cli.command()
@click.option("--event-id", required=True)
@click.option("--csv",      required=True)
@click.option("--resume",   is_flag=True, default=False,
              help="Skip people already processed for this event")
@click.option("--concurrency", default=5)
@click.option("--push-to-pi", is_flag=True, default=False)
async def research(event_id, csv, resume, concurrency, push_to_pi):
    rows = parse_csv(csv)

    if resume:
        done = await db.get_processed_names(event_id)
        rows = [r for r in rows if r.name not in done]
        click.echo(f"Resuming: {len(rows)} remaining of {len(parse_csv(csv))} total")

    await run_batch(rows, UUID(event_id), db, concurrency=concurrency)

    if push_to_pi:
        await push_to_pi_fn(event_id)
```

---

## LinkedIn scraping — account rotation + rate limiting

LinkedIn is the most sensitive source. Use multiple accounts rotating round-robin, with a minimum
15-second delay between any two LinkedIn requests regardless of which account is used.

```python
# agent/recon/sources/linkedin.py

import os, time, random, itertools
from open_linkedin_api import Linkedin  # pip install git+https://github.com/EseToni/open-linkedin-api.git

# Load multiple accounts from env
# Format: LINKEDIN_ACCOUNTS=email1:pass1,email2:pass2,email3:pass3
_accounts_raw = os.environ.get("LINKEDIN_ACCOUNTS", "").split(",")
_ACCOUNTS = [a.split(":") for a in _accounts_raw if ":" in a]
_account_pool = [Linkedin(email, pw) for email, pw in _ACCOUNTS]
_account_cycle = itertools.cycle(_account_pool)

_last_request_time: float = 0.0
MIN_DELAY_SECONDS = 15   # hard floor — never go below this between LinkedIn calls

def _get_next_account() -> Linkedin:
    return next(_account_cycle)

def _enforce_delay():
    global _last_request_time
    elapsed = time.time() - _last_request_time
    wait    = max(0, MIN_DELAY_SECONDS + random.uniform(0, 10) - elapsed)
    if wait > 0:
        time.sleep(wait)
    _last_request_time = time.time()

async def scrape_linkedin(linkedin_url: str | None) -> dict:
    if not linkedin_url:
        return {}

    public_id = linkedin_url.rstrip("/").split("/in/")[-1].split("/")[0]

    _enforce_delay()       # always wait before every LinkedIn call
    api = _get_next_account()

    try:
        profile = api.get_profile(public_id)
        posts   = api.get_profile_posts(public_id, post_count=20)
        return {"profile": profile, "posts": posts}
    except Exception as e:
        # Fallback: public profile via Playwright (no auth, less data but stable)
        return await scrape_linkedin_public_fallback(linkedin_url)

async def scrape_linkedin_public_fallback(url: str) -> dict:
    """
    Fallback if open-linkedin-api fails or gets rate limited.
    Scrapes the public LinkedIn profile page via Playwright (no login required).
    Gets ~70% of the data: name, headline, about, experience summary.
    """
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page    = await browser.new_page()
        await page.goto(url, wait_until="networkidle")
        text    = await page.inner_text("main")
        await browser.close()
        return {"public_text": text, "source": "playwright_fallback"}
```

### LinkedIn account setup in env

```
# agent/.env
# Add up to N accounts — more accounts = more headroom
# Each account rotates in round-robin; delay is per-account-pool, not per-account
LINKEDIN_ACCOUNTS=account1@email.com:password1,account2@email.com:password2,account3@email.com:password3
```

**Important:** disable 2FA on each LinkedIn account used for scraping.

---

## Input format — CSV + photos

### CSV format

```csv
name,company,role,linkedin_url,photo_path
Sarah Reyes,Vercel,Head of Product,https://linkedin.com/in/sreyes,photos/sarah_reyes.jpg
James Kim,Linear,Founding Eng,https://linkedin.com/in/jkim,
Aisha Mensah,a16z,Partner,,photos/aisha_mensah.jpg
Tom Lee,Retool,CEO,,
```

Column rules:
- `name` and `company` are required — used as the deduplication key
- `linkedin_url` optional — if missing, agent searches for it via Serper
- `photo_path` optional — local path relative to CSV file, or a URL
  - If provided: face matching runs to confirm identity and resolve missing social links
  - If omitted: face matching is skipped for this person

### Photo sourcing (your workflow options)

Before the event, you typically have access to:
- The event's speaker/attendee page (headshots)
- LinkedIn profile photos (can be added to CSV manually or scraped during identity resolution)
- Any pre-event materials from the organizer

The CSV `photo_path` column accepts either a local file path or a direct image URL. The agent
downloads URLs automatically before running face matching.

---

## Face matching

### Pre-event: identity confirmation (runs during pipeline, per CSV row)

```python
# agent/face_match/matcher.py

from deepface import DeepFace
import httpx, tempfile, os

async def resolve_identity_from_photo(photo_path_or_url: str,
                                      candidate_profiles: list[dict]) -> dict | None:
    """
    Given a photo and a list of candidate profiles (each with a photo_url),
    returns the best matching profile or None.

    Used during the pre-event pipeline when photo_path is set in the CSV.
    candidate_profiles typically = [the person found by name/company web search]
    This confirms the identity match before scraping their full profile.
    """
    # Download if URL
    local_path = await _ensure_local(photo_path_or_url)

    for candidate in candidate_profiles:
        if not candidate.get("photo_url"):
            continue
        candidate_local = await _ensure_local(candidate["photo_url"])
        try:
            result = DeepFace.verify(
                img1_path=local_path,
                img2_path=candidate_local,
                model_name="ArcFace",
                enforce_detection=False
            )
            if result["verified"] and result["distance"] < 0.4:
                return candidate
        except Exception:
            continue
    return None

async def _ensure_local(path_or_url: str) -> str:
    if path_or_url.startswith("http"):
        resp = await httpx.AsyncClient().get(path_or_url)
        tmp  = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        tmp.write(resp.content)
        tmp.close()
        return tmp.name
    return path_or_url
```

### At-event: identify unknown person (CLI command C)

```python
# run.py — identify subcommand

@cli.command()
@click.option("--photo", required=True, help="Path to photo of unknown person")
@click.option("--event-id", required=True, help="Search within this event's attendees")
@click.option("--threshold", default=0.4)
async def identify(photo, event_id, threshold):
    """
    At-event command: photograph someone, run this, get their profile.
    Compares the photo against all known attendees in the event.

    Usage: python run.py identify --photo shot.jpg --event-id <uuid>
    """
    attendees = await db.get_people_for_event(event_id)
    matches   = []

    for person in attendees:
        if not person.photo_url:
            continue
        try:
            result = DeepFace.verify(
                img1_path=photo,
                img2_path=await _ensure_local(person.photo_url),
                model_name="ArcFace",
                enforce_detection=False
            )
            if result["verified"] and result["distance"] < threshold:
                matches.append((person, result["distance"]))
        except Exception:
            continue

    if not matches:
        click.echo("No match found.")
        return

    matches.sort(key=lambda x: x[1])
    best, distance = matches[0]
    click.echo(f"Best match: {best.name} ({best.role} at {best.company})")
    click.echo(f"Confidence: {(1 - distance) * 100:.1f}%")
    click.echo(f"Profile: http://pi.local:3000/people/{best.id}")
```

---

## Scraping strategy — all sources

| Source | Method | Concurrency | Notes |
|---|---|---|---|
| LinkedIn | `open-linkedin-api` + Playwright fallback | 1 (serialized, 15s+ delay) | Account rotation, fallback on failure |
| Twitter/X | Playwright, public timeline | 5 | Treat as bonus signal — may be unreliable |
| Reddit | `praw` (official API) | 10 | Search by name + company |
| GitHub | GitHub REST API, unauthenticated | 10 | 60 req/hr limit, well within that |
| Instagram | `instaloader` library | 5 | Public profiles only |
| Company page | Playwright + BeautifulSoup | 5 | About + /careers or /jobs |
| Personal site | Playwright | 5 | Full text extraction |
| Web search | Serper API | 10 | Discovery + news + talks |

LinkedIn runs serialized at 1 concurrency regardless of the global `--concurrency` flag.
All other sources respect the flag. Set `--concurrency 10` for fast runs — LinkedIn will
pace itself automatically.

---

## LLM synthesis

### Model config

| Task | Primary | Fallback |
|---|---|---|
| Profile synthesis | `qwen2.5:32b` via Ollama | `claude-haiku-3-5` via Anthropic API |
| Message drafting (Pi) | `phi3.5:3.8b` via Ollama | `gemma2:2b` via Ollama |
| Face matching | DeepFace + ArcFace, fully local | — |

**On 24GB RAM:** `qwen2.5:32b` at Q4_K_M quantization uses ~20GB. M4 Pro unified memory handles
it at ~12–18 tok/s. Fine for an overnight batch job.

**Recommended workflow:** use `SYNTHESIS_BACKEND=anthropic` while tuning prompts (fast, ~$0.003
per profile), then switch to `SYNTHESIS_BACKEND=ollama` for production runs.

### Synthesis prompt

```python
# agent/synthesizer/prompts.py

SYNTHESIS_PROMPT = """
You are preparing a networking brief about a person before a professional event.
All data below was gathered from their public online presence.

PERSON: {name} — {role} at {company}

RAW DATA FROM SOURCES:
{raw_scrapes}

Produce a JSON object with EXACTLY this schema. No preamble. No markdown. JSON only.

{{
  "bio_snapshot": "3-4 sentences. Career arc, current focus, notable background, anything distinctive.",

  "talking_points": [
    {{
      "text": "Specific, concrete hook. Reference something they actually said or did. Not 'interested in AI' — instead 'Tweeted that LangChain's memory abstraction is broken for production, Feb 2025.'",
      "source": "Where this came from, e.g. 'Twitter, March 2025' or 'GitHub README'",
      "priority": 1
    }}
  ],

  "recon_sources": {{
    "linkedin":  {{"posts_found": 0, "summary": ""}},
    "twitter":   {{"posts_found": 0, "summary": ""}},
    "github":    {{"repos_found": 0, "summary": ""}},
    "reddit":    {{"posts_found": 0, "summary": ""}},
    "instagram": {{"posts_found": 0, "summary": ""}},
    "company":   {{"summary": ""}},
    "web":       {{"summary": ""}}
  }}
}}

Rules:
- talking_points: 3-5 items ranked by conversational impact (1 = strongest opener).
- Never hallucinate. Empty source = empty summary.
- Prioritize recency. Last month beats last year.
- If a source failed or returned nothing, leave its summary as empty string.
- open_roles are NOT included here — they are scraped separately per event.
"""
```

### Message drafting prompt (Pi)

```python
# server/drafter/prompts.py

DRAFT_PROMPT = """
Write a short follow-up message from {my_name} to {their_name} after meeting at a professional event.

WHO THEY ARE:
- {role} at {company}
- Key thing about them: {top_talking_point}

WHAT WE TALKED ABOUT:
{met_notes}

SEND CHANNEL: {channel}  (linkedin_dm | email | twitter_dm)

Rules:
- 3-5 sentences. No longer.
- Reference something SPECIFIC from the conversation notes.
- End with one natural, low-pressure hook — a question, resource offer, or shared next step.
- Adjust tone for channel: email slightly more formal, DMs shorter and more casual.
- Do NOT open with "It was great meeting you at [event name]".
- Do NOT use: synergy, leverage, circle back, touch base, reach out, connect.
- Tone: warm and direct. Like a message you'd actually want to receive.

Return ONLY the message text. Nothing else.
"""
```

---

## API routes (FastAPI)

```
# Events
GET    /api/events                          list all events with people_count, met_count
POST   /api/events                          create event
GET    /api/events/{id}                     event detail
PATCH  /api/events/{id}                     update event
DELETE /api/events/{id}                     delete + cascade attendances

# People + attendance (combined view for the app)
GET    /api/events/{event_id}/people        list attendances for event; ?met=true|false&q=search
                                            returns Person fields merged with EventAttendance fields
GET    /api/people/{id}                     global person detail (bio, talking_points, recon_sources)
GET    /api/attendance/{id}                 attendance detail (met, notes, outreach, open_roles)
PATCH  /api/people/{id}                     update person fields

# Ingest (Mac → Pi)
POST   /api/ingest                          receive agent output from Mac
       header: X-Ingest-Secret: <PI_API_SECRET>
       body:   { event_id, people: [PersonProfile, ...] }
       behavior: upserts Person by (name, company), upserts EventAttendance by (person_id, event_id)
                 safe to call multiple times — idempotent

# Met flow
POST   /api/attendance/{id}/met             flip met toggle + save notes
       body:   { met: bool, notes: str }
       effect: if met=true, enqueues background draft generation (Celery)

# Outreach
POST   /api/outreach/draft                  call Pi's small LLM, return draft
       body:   { attendance_id, channel, extra_context }
       returns: { draft: str }

POST   /api/outreach/send                   enqueue Celery send task
       body:   { attendance_id, channel, message }
       returns: { task_id, status: "queued" }

GET    /api/outreach/status/{task_id}       poll send status
       returns: { status: "queued"|"sent"|"failed", error? }
```

### Ingest idempotency (important for large batches)

```python
# server/api/routes/ingest.py

async def upsert_person_and_attendance(profile: PersonProfile, event_id: UUID, db):
    """
    Called once per person during ingest. Fully idempotent — safe to re-run.
    """
    # Upsert Person by (name, company) — update if exists, create if not
    person = await db.execute(
        insert(Person)
        .values(**profile.person_fields())
        .on_conflict_do_update(
            index_elements=["name", "company"],
            set_=profile.person_fields()
        )
        .returning(Person)
    )

    # Upsert EventAttendance by (person_id, event_id)
    # UniqueConstraint("person_id", "event_id") ensures one row per pair
    await db.execute(
        insert(EventAttendance)
        .values(person_id=person.id, event_id=event_id,
                open_roles=profile.open_roles)
        .on_conflict_do_update(
            constraint="uq_person_event",
            set_={"open_roles": profile.open_roles}
            # NOTE: never overwrite met, met_notes, outreach — those are user data
        )
    )
```

---

## LinkedIn DM sending (Pi side)

The official LinkedIn API does not support DM sending for personal accounts.
Use Playwright with a saved browser session. One-time setup required.

```python
# server/outreach/linkedin.py

import os
from playwright.async_api import async_playwright

AUTH_STATE = os.environ.get("LINKEDIN_AUTH_STATE_PATH", "linkedin_auth.json")

async def send_linkedin_dm(profile_url: str, message: str) -> bool:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=AUTH_STATE)
        page    = await context.new_page()
        await page.goto(profile_url, wait_until="networkidle")
        await page.click('[aria-label="Message"]')
        await page.wait_for_selector('.msg-form__contenteditable')
        await page.fill('.msg-form__contenteditable', message)
        await page.click('.msg-form__send-button')
        await page.wait_for_timeout(1500)
        await browser.close()
        return True
```

```python
# agent/setup_linkedin_auth.py
# Run once on the Pi to save the LinkedIn session cookie.
# Re-run if LinkedIn logs you out.

import asyncio
from playwright.async_api import async_playwright

async def save_auth():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page    = await context.new_page()
        await page.goto("https://www.linkedin.com/login")
        input("Log in manually in the browser window, then press Enter here...")
        await context.storage_state(path="linkedin_auth.json")
        await browser.close()
        print("Saved to linkedin_auth.json")

asyncio.run(save_auth())
```

---

## Outreach deduplication + safety checks

```python
# server/tasks/send_task.py

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_outreach_task(self, attendance_id: str, channel: str, message: str):
    db   = get_db_session()
    att  = db.query(EventAttendance).get(attendance_id)

    # Safety checks — never double-send
    if att.outreach_sent:
        logger.warning(f"Outreach already sent for attendance {attendance_id} — aborting")
        return

    if not att.met:
        logger.warning(f"Attendance {attendance_id} not marked as met — aborting")
        return

    try:
        if channel == "linkedin":
            send_linkedin_dm(att.person.linkedin_url, message)
        elif channel == "email":
            send_gmail(att.person.email, message)
        elif channel == "twitter":
            send_twitter_dm(att.person.twitter_handle, message)

        att.outreach_sent    = True
        att.outreach_channel = channel
        att.outreach_draft   = message
        att.outreach_sent_at = datetime.utcnow()
        db.commit()

    except Exception as exc:
        raise self.retry(exc=exc)
```

---

## PWA + offline caching

The app needs to work even if home internet hiccups during the event.
Implement a service worker using `vite-plugin-pwa`.

```typescript
// src/sw.ts — service worker strategy

// Cache all API GET responses for offline read access
// Queue POST/PATCH requests when offline and flush on reconnect

const CACHE_NAME    = "event-intel-v1"
const API_BASE      = "http://pi.local:8000/api"
const OFFLINE_QUEUE = "offline-queue"

// Cache strategy: Network first, fall back to cache
// Applied to: /api/events, /api/events/*/people, /api/people/*, /api/attendance/*
self.addEventListener("fetch", (event) => {
  if (event.request.method === "GET" && event.request.url.includes(API_BASE)) {
    event.respondWith(networkFirstWithCache(event.request))
  }
  if (["POST", "PATCH"].includes(event.request.method)) {
    event.respondWith(queueIfOffline(event.request))
  }
})

// On reconnect: flush queued mutations (met toggles, outreach sends)
self.addEventListener("sync", (event) => {
  if (event.tag === "flush-queue") {
    event.waitUntil(flushOfflineQueue())
  }
})
```

What works offline:
- Browsing all event tabs and attendee lists (cached GET responses)
- Reading any person's full profile page
- Toggling met and adding notes (queued, synced on reconnect)

What requires connectivity:
- Draft generation (LLM call to Pi)
- Sending outreach messages

---

## Environment variables

### Mac — `agent/.env`

```
# LLM
SYNTHESIS_BACKEND=anthropic            # "ollama" or "anthropic"
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:32b
ANTHROPIC_API_KEY=sk-ant-...

# Scraping
SERPER_API_KEY=...
LINKEDIN_ACCOUNTS=email1@x.com:pass1,email2@x.com:pass2,email3@x.com:pass3

# Pi
PI_URL=http://pi.local:8000
PI_API_SECRET=...

# Personal
MY_NAME=...
```

### Pi — `server/.env`

```
# Database
DATABASE_URL=postgresql://eventintel:password@localhost/eventintel

# Queue
REDIS_URL=redis://localhost:6379

# LLM
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=phi3.5:3.8b

# Ingest auth
PI_API_SECRET=...

# LinkedIn (for DM sending via Playwright)
LINKEDIN_AUTH_STATE_PATH=/home/pi/event-intel/linkedin_auth.json

# Gmail
GMAIL_ADDRESS=...
GMAIL_APP_PASSWORD=...

# Twitter
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_TOKEN_SECRET=...

# App
MY_NAME=...
```

---

## Mac CLI — all commands

```bash
# Create a new event on the Pi
python run.py new-event \
  --name "SaaStr Annual 2025" \
  --date-start 2025-09-10 \
  --date-end 2025-09-12 \
  --location "San Mateo, CA" \
  --tags "SaaS,B2B,Founders" \
  --color "#7F77DD"

# Run the full agent pipeline on an attendee CSV
# CSV: name, company, role, linkedin_url (optional), photo_path (optional)
python run.py research \
  --event-id <uuid> \
  --csv attendees.csv \
  --concurrency 10 \       # LinkedIn always runs at 1 regardless
  --push-to-pi             # sync to Pi when done

# Resume an interrupted run (skips already-processed people)
python run.py research \
  --event-id <uuid> \
  --csv attendees.csv \
  --resume \
  --push-to-pi

# Research a single person (useful for testing)
python run.py research-one \
  --event-id <uuid> \
  --name "Sarah Reyes" \
  --company "Vercel" \
  --push-to-pi

# Manually sync already-researched profiles to Pi (no re-scraping)
python run.py sync --event-id <uuid>

# At-event: identify unknown person from a photo
python run.py identify \
  --photo shot.jpg \
  --event-id <uuid>
# Prints best match + confidence + profile URL
```

---

## Pi deployment

```bash
# System deps
sudo apt update && sudo apt install -y postgresql redis-server nginx python3-pip

# Postgres
sudo -u postgres psql -c "CREATE USER eventintel WITH PASSWORD 'password';"
sudo -u postgres psql -c "CREATE DATABASE eventintel OWNER eventintel;"

# Python deps
pip3 install fastapi uvicorn sqlalchemy alembic psycopg2-binary \
             celery redis httpx playwright ollama python-dotenv tweepy
playwright install chromium

# Run migrations
cd /home/pi/event-intel/server && alembic upgrade head

# Systemd services (or run in tmux during dev)
uvicorn server.api.main:app --host 0.0.0.0 --port 8000 --workers 2
celery -A server.tasks.celery_app worker --loglevel=info

# Nginx
# - Proxy / → localhost:8000
# - Serve /home/pi/event-intel/app/dist as static files
# - pi.local resolves via mDNS on local network

# One-time LinkedIn sender auth (headed browser on Pi)
python agent/setup_linkedin_auth.py
```

---

## Key third-party dependencies

```
# agent/requirements.txt  (Mac)
langgraph>=0.2
langchain-core>=0.3
playwright>=1.44
anthropic>=0.28
httpx>=0.27
praw>=7.7
instaloader>=4.10
deepface>=0.0.93
opencv-python-headless
python-dotenv
click
# LinkedIn — install from GitHub:
# pip install git+https://github.com/EseToni/open-linkedin-api.git

# server/requirements.txt  (Pi)
fastapi>=0.111
uvicorn>=0.30
sqlalchemy>=2.0
alembic>=1.13
psycopg2-binary
celery>=5.4
redis>=5.0
playwright>=1.44
ollama>=0.2
httpx>=0.27
python-dotenv
tweepy>=4.14

# app/package.json (React PWA)
# react, react-dom, react-router-dom, axios, typescript
# vite, vite-plugin-pwa
```

---

## Frontend behavior spec

### Event tab system
- Top tab bar: one tab per event ordered by date descending, plus "Add event" button
- Each tab: colored dot (from `event.color`), event name, person count badge
- Active tab stored in `localStorage` — survives refresh
- Switching tabs updates event header and people grid below

### Event header
- Event name, date range, location, tags as pills
- Stats: total / met / still to meet — live as you toggle met

### Person card (2-column grid on mobile)
- Avatar: photo if available, else initials colored by name hash
- Name, role, company
- Top talking point (2 lines, truncated)
- Met badge (green) or "not met" (muted)
- Source icons showing which sources returned data
- Green left border when met = true
- Tap card → PersonProfile page
- Met toggle on card → MetModal

### MetModal flow
1. Confirm: "You met [Name] at [Event]" + undo option
2. Context: their top talking point shown for reference (not editable)
3. Notes: textarea "What did you talk about?" — optional, strongly encouraged
4. Channel: pills for available channels (only show if data exists for that channel)
5. Draft: button → POST /api/outreach/draft → streams into editable textarea
6. Send / Save draft / Skip

### PersonProfile page
- Back → event tab, preserves scroll position
- Hero: avatar, name, role + company + location, social link pills, met badge + toggle
- Three tabs:
  - Overview: talking points (numbered, sourced), bio snapshot, open roles
  - Recon data: per-source breakdown (posts found, summary)
  - Outreach: draft/send panel, sent message history
- "Mark as met & send follow-up" CTA at bottom when not yet met

---

## Build order

Follow this order. Each step is independently testable before moving on.

1. **DB schema + migrations** — run `alembic upgrade head`, verify all 3 tables exist including `UniqueConstraint` on `event_attendances`
2. **FastAPI skeleton** — all routes stubbed with hardcoded mock responses; no DB yet
3. **DB integration** — wire all routes to Postgres; test CRUD with curl
4. **Ingest endpoint** — implement upsert logic; test with a hand-crafted JSON payload
5. **React PWA** — EventTabs, EventDetail, PersonCard, PersonProfile, MetModal — against mock API with fixture data
6. **Connect frontend to live API** — replace fixtures with real calls; test full UI flow with manually inserted DB rows
7. **Service worker** — offline read cache + write queue; test by disconnecting Pi mid-session
8. **Agent: web.py** — Serper search, simplest source; test standalone
9. **Agent: github.py, reddit.py, instagram.py, company.py** — one at a time, test standalone
10. **Agent: linkedin.py** — account rotation + delay + fallback; test with one profile
11. **Agent: twitter.py** — add last; treat as optional/bonus
12. **LangGraph orchestrator** — wire all sources; test single person end-to-end
13. **Synthesizer** — connect to Anthropic API first; tune until talking points are genuinely specific; switch to Ollama after
14. **Mac CLI** — all subcommands including `--resume` and `identify`; full CSV test
15. **Face matching** — pre-event (CSV photo_path) and at-event (`identify` command)
16. **Pi drafter** — POST /api/outreach/draft with phi3.5; test via MetModal
17. **Outreach senders** — Gmail first, Twitter, LinkedIn Playwright last
18. **Polish** — PWA manifest, mobile layout, loading/error states, Nginx config

---

*End of spec. Hand to Claude Code with: "Scaffold this project exactly as described. Start with step 1 of the build order."*