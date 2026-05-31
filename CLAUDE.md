# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## What this is

A personal event networking tool. A Mac-side agent pipeline researches every attendee pre-event and produces rich profiles (talking points, bio, open roles, conversation hooks). At the event, you browse profiles on your phone via a React PWA served from a Raspberry Pi. After meeting someone, you flip a "met" toggle and the Pi drafts and sends a personalized follow-up via LinkedIn, email, or Twitter.

---

## Hardware split

| Machine | Role |
|---|---|
| MacBook M4 Pro (24GB RAM) | One-time pre-event agent pipeline: scraping, face matching, LLM synthesis |
| Raspberry Pi (always on) | App server: FastAPI, PostgreSQL, Redis, small-model drafting, outreach sending |
| iPhone (browser) | PWA client used at the event |

The `agent/` directory only runs on the Mac. The `server/` and `app/` directories deploy to the Pi.

---

## Running the system

### Mac agent (pre-event)

```bash
# One-time LinkedIn auth setup
python agent/setup_linkedin_auth.py

# Create a new event
python agent/run.py new-event --name "SaaStr Annual 2025" --date-start 2025-09-10 --date-end 2025-09-12 --location "San Francisco"

# Run full batch research from a CSV
python agent/run.py research --event-id <uuid> --csv attendees.csv --concurrency 10 --push-to-pi

# Resume a crashed batch (skips already-processed rows)
python agent/run.py research --event-id <uuid> --csv attendees.csv --resume --push-to-pi

# Research a single person
python agent/run.py research-one --event-id <uuid> --name "Jane Smith" --company "Acme Corp" --push-to-pi

# Re-sync all processed people for an event to Pi
python agent/run.py sync --event-id <uuid>

# Identify someone from a photo
python agent/run.py identify --photo shot.jpg --event-id <uuid>
```

### Pi server

```bash
# Run DB migrations
cd server && alembic upgrade head

# Start API server
uvicorn server.api.main:app --host 0.0.0.0 --port 8000 --workers 2

# Start Celery worker for async outreach
celery -A server.tasks.celery_app worker --loglevel=info
```

### React PWA (build on Mac, serve from Pi)

```bash
cd app
npm install
npm run dev        # local dev against Pi at pi.local:8000
npm run build      # output to app/dist/ — copy to Pi
```

---

## Architecture

### Database schema (3 tables)

The core architectural decision: `Person` is **global** (scraped once, reused across events). `EventAttendance` is the join table holding all **per-event state**. This enables ~1000 attendees across multiple events without re-scraping repeat attendees.

- `Event` — event metadata (name, dates, tags, color)
- `Person` — global profile: identity, social links, `bio_snapshot`, `talking_points` (JSONB), `recon_sources` (JSONB), `raw_intel` (JSONB), `agent_ran_at`
- `EventAttendance` — per-event state: `open_roles`, `met`, `met_notes`, `outreach_draft`, `outreach_sent`. Unique constraint on `(person_id, event_id)`.

### Agent pipeline (Mac)

LangGraph orchestrator in `agent/recon/orchestrator.py` drives a deduplication + freshness decision tree before any scraping:

- **Already processed this event** → skip
- **Profile fresh (< 90 days)** → skip full scrape, only re-scrape open roles (30-day freshness)
- **Profile stale or new** → full pipeline: 7 scrapers → face matching → LLM synthesis → POST to Pi

Scrapers: LinkedIn (open-linkedin-api + Playwright fallback, 15s+ delays, account rotation), Twitter (Playwright), Reddit (PRAW), GitHub (REST API), Instagram (instaloader), Company/careers page (Playwright), Web (Serper API).

Synthesis: routes to Ollama (qwen2.5:32b local) or Anthropic API (Claude Haiku fallback) via `agent/synthesizer/synthesizer.py`.

Writes to DB immediately after each person succeeds — crash-safe and resumable.

### Server (Pi)

FastAPI app at `server/api/main.py`. Key routes:
- `POST /api/ingest` — idempotent upsert from Mac (uses `INSERT ON CONFLICT DO UPDATE`)
- `POST /api/attendance/{id}/met` — toggle met state, enqueues Celery outreach task
- `POST /api/outreach/draft` — calls Ollama phi3.5:3.8b on Pi
- `POST /api/outreach/send` — validates `outreach_sent=false` and `met=true` before sending

Outreach senders in `server/outreach/`: LinkedIn (Playwright), Gmail (SMTP), Twitter (API v2). Celery + Redis handles async send with retries.

### React PWA (app/)

Vite + TypeScript + vite-plugin-pwa. `src/api/client.ts` is an Axios instance pointing to `pi.local:8000`.

Key components:
- `EventTabs` — top-level tab per event
- `EventDetail` — attendee card grid (main at-event view)
- `PersonProfile` — full detail page with tabs: bio, talking points, recon data, outreach
- `MetModal` — confirm → notes → channel → draft → send flow
- `sw.ts` — service worker caches all GETs, queues POSTs for offline use, syncs on reconnect

---

## Critical invariants

- **Ingest idempotency**: `POST /api/ingest` is safe to call multiple times — uses PostgreSQL `INSERT ON CONFLICT DO UPDATE`.
- **Outreach safety**: Never double-send. Check `outreach_sent=false` AND `met=true` before any send. Celery retries use exponential backoff.
- **Resume safety**: Batch runner writes each person to DB immediately on success. On resume, the orchestrator checks `EventAttendance` for existing rows and skips them.
- **LinkedIn rate limiting**: Enforce 15+ second delay between any LinkedIn calls. Use account rotation. Playwright fallback if API fails.

---

## Environment variables

`agent/.env`:
```
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:32b
ANTHROPIC_API_KEY=...
SERPER_API_KEY=...
PI_BASE_URL=http://pi.local:8000
INGEST_SECRET=...
LINKEDIN_ACCOUNTS=email1:pass1,email2:pass2
MY_NAME=...
MY_ROLE=...
MY_COMPANY=...
LINKEDIN_SESSION_PATH=~/.linkedin_session
```

`server/.env`:
```
DATABASE_URL=postgresql://user:pass@localhost:5432/eventintel
REDIS_URL=redis://localhost:6379
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_DRAFT_MODEL=phi3.5:3.8b
INGEST_SECRET=...
LINKEDIN_SESSION_PATH=/home/pi/.linkedin_session
GMAIL_ADDRESS=...
GMAIL_APP_PASSWORD=...
TWITTER_BEARER_TOKEN=...
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_SECRET=...
```

---

## Build order

Follow this order when scaffolding from scratch:

1. DB schema + Alembic migration
2. FastAPI skeleton with mocked responses
3. Wire DB into routes
4. `POST /api/ingest` endpoint
5. React PWA against fixture data
6. Connect frontend to live API
7. Service worker (offline cache + mutation queue)
8. Scraper sources: web → github → reddit → instagram → company
9. `linkedin.py` with account rotation
10. `twitter.py`
11. LangGraph orchestrator
12. Synthesizer (Anthropic first, Ollama fallback)
13. Mac CLI (`run.py`)
14. Face matching (`matcher.py` + `resolver.py`)
15. Pi drafter (phi3.5 via Ollama)
16. Outreach senders (LinkedIn, Gmail, Twitter)
17. Polish + PWA manifest
