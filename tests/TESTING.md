# Phase-by-phase testing guide

You develop on Mac, deploy to Pi. The strategy: run Postgres + Redis in Docker locally on your Mac so the environment matches the Pi exactly. Each phase has a test you run before moving on.

---

## One-time Mac setup

```bash
# Docker Desktop must be running (only needed for Redis — local Homebrew Postgres is used instead)
docker compose up -d          # starts Redis:6379 (Postgres mapped to 5433 to avoid Homebrew conflict)

# Create the local Postgres role + database (only needed once)
psql postgres -c "CREATE USER eventintel WITH PASSWORD 'password';"
psql postgres -c "CREATE DATABASE eventintel OWNER eventintel;"

# Install server deps
python3 -m venv venv && source venv/bin/activate
pip install -r server/requirements.txt

# Copy env (DATABASE_URL points to local Postgres, Redis to Docker)
cp server/.env.example server/.env
# Edit server/.env:
#   DATABASE_URL=postgresql://eventintel:password@localhost/eventintel
#   REDIS_URL=redis://localhost:6379
#   PI_API_SECRET=changeme

# Run migrations (from project root)
cd server && PYTHONPATH=.. alembic upgrade head && cd ..

# Start server in a separate terminal (always from project root)
PYTHONPATH=. uvicorn server.api.main:app --reload
```

---

## Phase 1 — DB + FastAPI + Ingest

**What's tested:** all CRUD routes, ingest idempotency, met toggle, cascade delete, ingest doesn't overwrite user data.

```bash
pip install requests   # one-time
python tests/test_phase1.py
```

Expected: all green. The test creates an event, ingests 2 people, exercises every route, and cleans up.

---

## Phase 2 — React PWA (frontend against fixture data)

Start the dev server and open on your phone (same WiFi as Mac):

```bash
cd app && npm run dev -- --host
# Opens at http://<your-mac-ip>:5173
```

Manual checklist:
- [ ] EventTabs renders one tab per event in the DB
- [ ] Switching tabs updates the attendee grid
- [ ] PersonCard shows name, role, company, top talking point
- [ ] Tapping a card opens PersonProfile with all three tabs (Overview / Recon / Outreach)
- [ ] Met toggle on card opens MetModal — confirm → notes → channel → draft → send flow renders

---

## Phase 3 — Connect frontend to live API

Edit `app/src/api/client.ts` to point at `http://localhost:8000` during dev.

Manual checklist:
- [ ] EventTabs populates from `GET /api/events` (not fixtures)
- [ ] People grid populates from `GET /api/events/{id}/people`
- [ ] Met toggle calls `POST /api/attendance/{id}/met` and UI updates immediately
- [ ] Stats bar (total / met / to meet) updates live as you toggle
- [ ] Search box filters people in real time

---

## Phase 4 — Service worker (offline cache)

```bash
cd app && npm run build && npx serve dist
```

Manual checklist using Chrome DevTools → Network tab → set to Offline:
- [ ] All event tabs still render from cache
- [ ] All person profiles still load
- [ ] Met toggle while offline: UI optimistically updates, no error shown
- [ ] Go back online: queued POST flushes and DB updates
- [ ] Reconnect check: `GET /api/attendance/{id}` returns met=true

---

## Phase 5 — Agent: individual scrapers

Test each scraper standalone before wiring into the orchestrator.

```bash
# From project root, with agent/.env set
cd agent

# web.py
python -c "
import asyncio
from recon.sources.web import scrape_web
result = asyncio.run(scrape_web('Sarah Guo', 'Conviction'))
print(result)
"

# github.py, reddit.py, instagram.py, company.py — same pattern
# Each should return a dict with source data, not raise an exception
```

Pass criteria: each returns a dict (even if empty `{}`), no unhandled exceptions.

---

## Phase 6 — LinkedIn scraper

LinkedIn runs separately because of the 15s delay requirement.

```bash
cd agent
python -c "
import asyncio
from recon.sources.linkedin import scrape_linkedin
result = asyncio.run(scrape_linkedin('https://linkedin.com/in/someonereal'))
print('posts found:', len(result.get('posts', [])))
print('profile keys:', list(result.get('profile', {}).keys()))
"
```

Pass criteria: returns profile data without raising, waits ~15s between calls if you run twice.

---

## Phase 7 — LangGraph orchestrator (single person end-to-end)

```bash
cd agent
python run.py research-one \
  --event-id <uuid-from-phase1> \
  --name "Sarah Guo" \
  --company "Conviction" \
  --push-to-pi
```

Then verify in the DB:
```bash
psql postgresql://eventintel:password@localhost/eventintel \
  -c "SELECT name, company, agent_ran_at, jsonb_array_length(talking_points) FROM people WHERE name='Sarah Guo';"
```

Pass criteria: row exists, `agent_ran_at` is set, `talking_points` has 3–5 items.

---

## Phase 8 — Full CSV batch + resume

```bash
# Run on a small CSV (5-10 rows)
cd agent
python run.py research --event-id <uuid> --csv test_attendees.csv --concurrency 5 --push-to-pi

# Kill mid-run (Ctrl+C), then:
python run.py research --event-id <uuid> --csv test_attendees.csv --resume --push-to-pi
```

Pass criteria: resume skips already-processed rows (check log output for `SKIP` lines), final count matches CSV row count.

---

## Phase 9 — Drafter (Pi LLM)

Requires Ollama running with `phi3.5:3.8b` pulled.

```bash
# With server running and Ollama running:
curl -s -X POST http://localhost:8000/api/outreach/draft \
  -H "Content-Type: application/json" \
  -d '{
    "attendance_id": "<attendance-id-where-met=true>",
    "channel": "linkedin",
    "extra_context": "We talked about serverless cold starts"
  }' | python3 -m json.tool
```

Pass criteria: returns a `draft` string, 3–5 sentences, no banned phrases (synergy, touch base, etc.).

---

## Phase 10 — Outreach send (Gmail first)

Test Gmail only — it's the easiest to verify without side effects.

```bash
curl -s -X POST http://localhost:8000/api/outreach/send \
  -H "Content-Type: application/json" \
  -d '{
    "attendance_id": "<id>",
    "channel": "email",
    "message": "Test outreach message"
  }' | python3 -m json.tool

# Poll status
curl http://localhost:8000/api/outreach/status/<task-id>
```

Pass criteria: email arrives in inbox, `outreach_sent=true` in DB, second send attempt returns 409.

---

## Deploying to Pi

Once a phase is working locally, push to Pi and re-run the same tests against `http://pi.local:8000`:

```bash
# On Mac — sync code to Pi
rsync -av --exclude '.venv' --exclude '__pycache__' \
  "/Users/ayushpathak/Documents/Personal Projects/nytw-guide/" \
  pi@pi.local:/home/pi/event-intel/

# On Pi — migrate + restart
ssh pi@pi.local "cd /home/pi/event-intel/server && alembic upgrade head"
ssh pi@pi.local "sudo systemctl restart eventintel"

# Re-run Phase 1 tests against Pi
BASE_URL=http://pi.local:8000 python tests/test_phase1.py  # (update BASE at top of script)
```
