#!/usr/bin/env python3
"""
Phase 1 test suite — DB schema + FastAPI + DB integration + ingest endpoint.

Run from project root:
    python tests/test_phase1.py

Requires:
    pip install requests
    Server running: uvicorn server.api.main:app --reload (from server/ with .env set)
"""

import sys
import requests
from requests.exceptions import ConnectionError

BASE = "http://localhost:8000"
INGEST_SECRET = "changeme"  # must match PI_API_SECRET in server/.env

PASS = "\033[92m PASS\033[0m"
FAIL = "\033[91m FAIL\033[0m"

_failures = []


def check(label: str, condition: bool, detail: str = ""):
    if condition:
        print(f"{PASS}  {label}")
    else:
        print(f"{FAIL}  {label}" + (f" — {detail}" if detail else ""))
        _failures.append(label)


def r(method, path, **kwargs):
    try:
        resp = getattr(requests, method)(f"{BASE}{path}", **kwargs)
        return resp
    except ConnectionError:
        print(f"\n\033[91mCannot connect to {BASE}\033[0m")
        print("Start the server first:\n")
        print("  cd /Users/ayushpathak/Documents/Personal\\ Projects/nytw-guide")
        print("  uvicorn server.api.main:app --reload\n")
        sys.exit(1)


# ── Health ────────────────────────────────────────────────────────────────────

print("\n── Health ──")
resp = r("get", "/health")
check("GET /health → 200", resp.status_code == 200)
check("GET /health → {status: ok}", resp.json().get("status") == "ok")


# ── Events CRUD ───────────────────────────────────────────────────────────────

print("\n── Events ──")

resp = r("post", "/api/events", json={
    "name": "Test Event",
    "date_start": "2025-09-10",
    "date_end": "2025-09-12",
    "location": "San Francisco",
    "tags": ["SaaS", "B2B"],
    "color": "#7F77DD",
})
check("POST /api/events → 201", resp.status_code == 201)
event_id = resp.json().get("id")
check("POST /api/events returns id", bool(event_id), str(resp.json()))

resp = r("get", "/api/events")
check("GET /api/events → 200", resp.status_code == 200)
check("GET /api/events returns list", isinstance(resp.json(), list))
check("Event appears in list", any(e["id"] == event_id for e in resp.json()))
check("Event has people_count field", "people_count" in resp.json()[0])
check("Event has met_count field", "met_count" in resp.json()[0])

resp = r("get", f"/api/events/{event_id}")
check("GET /api/events/{id} → 200", resp.status_code == 200)
check("GET /api/events/{id} correct name", resp.json().get("name") == "Test Event")

resp = r("patch", f"/api/events/{event_id}", json={"location": "San Mateo"})
check("PATCH /api/events/{id} → 200", resp.status_code == 200)
check("PATCH updates field", resp.json().get("location") == "San Mateo")

resp = r("get", f"/api/events/00000000-0000-0000-0000-000000000000")
check("GET /api/events/{bad-id} → 404", resp.status_code == 404)


# ── Ingest ────────────────────────────────────────────────────────────────────

print("\n── Ingest ──")

ingest_payload = {
    "event_id": event_id,
    "people": [
        {
            "name": "Alice Chen",
            "company": "Vercel",
            "role": "Head of Product",
            "linkedin_url": "https://linkedin.com/in/alicechen",
            "bio_snapshot": "Former PM at Stripe, now leading product at Vercel.",
            "talking_points": [
                {"text": "Tweeted that Next.js 15 caching model is finally right", "source": "Twitter, March 2025", "priority": 1},
                {"text": "Open sourced a cost calculator for Vercel deployments", "source": "GitHub, Jan 2025", "priority": 2},
            ],
            "recon_sources": {
                "linkedin": {"posts_found": 4, "summary": "Mostly product strategy posts"},
                "twitter": {"posts_found": 12, "summary": "Technical takes on web perf"},
                "github": {"repos_found": 3, "summary": ""},
            },
            "open_roles": [
                {"title": "Senior PM", "dept": "Product", "location": "Remote", "url": "https://vercel.com/careers/senior-pm"},
            ],
        },
        {
            "name": "Bob Kim",
            "company": "Linear",
            "role": "Founding Engineer",
            "github_handle": "bobkim",
            "bio_snapshot": "Early engineer at Linear, obsessed with performance.",
            "talking_points": [
                {"text": "Wrote a blog post about eliminating re-renders in React with fine-grained subscriptions", "source": "Personal site, Feb 2025", "priority": 1},
            ],
            "recon_sources": {
                "github": {"repos_found": 21, "summary": "Heavy open source contributor"},
                "twitter": {"posts_found": 0, "summary": ""},
            },
            "open_roles": [],
        },
    ],
}

headers = {"X-Ingest-Secret": INGEST_SECRET}

resp = r("post", "/api/ingest", json=ingest_payload, headers=headers)
check("POST /api/ingest → 200", resp.status_code == 200)
check("POST /api/ingest upserted=2", resp.json().get("upserted") == 2, str(resp.json()))

# Idempotency: run again, same result, no duplicates
resp2 = r("post", "/api/ingest", json=ingest_payload, headers=headers)
check("POST /api/ingest idempotent (200 on re-run)", resp2.status_code == 200)
check("POST /api/ingest idempotent (upserted=2 again)", resp2.json().get("upserted") == 2)

resp = r("post", "/api/ingest", json=ingest_payload, headers={"X-Ingest-Secret": "wrong"})
check("POST /api/ingest rejects bad secret → 401", resp.status_code == 401)


# ── People + Attendance ───────────────────────────────────────────────────────

print("\n── People + Attendance ──")

resp = r("get", f"/api/events/{event_id}/people")
check("GET /api/events/{id}/people → 200", resp.status_code == 200)
people = resp.json()
check("Returns 2 people", len(people) == 2, f"got {len(people)}")
check("People have attendance_id", all("attendance_id" in p for p in people))
check("People have talking_points", any(p.get("talking_points") for p in people))
check("People have open_roles", any(p.get("open_roles") for p in people))

alice = next((p for p in people if p["name"] == "Alice Chen"), None)
check("Alice Chen present", alice is not None)

attendance_id = alice["attendance_id"] if alice else None
person_id = alice["person_id"] if alice else None

resp = r("get", f"/api/events/{event_id}/people?met=false")
check("GET people?met=false returns only unmet", all(not p["met"] for p in resp.json()))

resp = r("get", f"/api/events/{event_id}/people?q=alice")
check("GET people?q=alice search works", len(resp.json()) == 1)

resp = r("get", f"/api/people/{person_id}")
check("GET /api/people/{id} → 200", resp.status_code == 200)
check("Person has bio_snapshot", bool(resp.json().get("bio_snapshot")))

resp = r("get", f"/api/attendance/{attendance_id}")
check("GET /api/attendance/{id} → 200", resp.status_code == 200)
check("Attendance met=false initially", resp.json().get("met") == False)

resp = r("patch", f"/api/people/{person_id}", json={"role": "VP Product"})
check("PATCH /api/people/{id} → 200", resp.status_code == 200)
check("PATCH updates role", resp.json().get("role") == "VP Product")


# ── Met toggle ────────────────────────────────────────────────────────────────

print("\n── Met toggle ──")

resp = r("post", f"/api/attendance/{attendance_id}/met", json={"met": True, "notes": "Talked about Next.js caching"})
check("POST /api/attendance/{id}/met → 200", resp.status_code == 200)
check("met=true after toggle", resp.json().get("met") == True)
check("met_notes saved", resp.json().get("met_notes") == "Talked about Next.js caching")
check("met_at is set", bool(resp.json().get("met_at")))

resp = r("get", f"/api/events/{event_id}/people?met=true")
check("GET people?met=true now returns Alice", len(resp.json()) == 1)

# Toggle back off
resp = r("post", f"/api/attendance/{attendance_id}/met", json={"met": False})
check("Met toggle back to false", resp.json().get("met") == False)


# ── Ingest protects user data ─────────────────────────────────────────────────

print("\n── Ingest doesn't overwrite user data ──")

# Re-ingest with different open_roles, verify met/notes are preserved
r("post", f"/api/attendance/{attendance_id}/met", json={"met": True, "notes": "Keep this note"})
modified_payload = {**ingest_payload, "people": [{**ingest_payload["people"][0], "open_roles": []}]}
r("post", "/api/ingest", json=modified_payload, headers=headers)

resp = r("get", f"/api/attendance/{attendance_id}")
check("Re-ingest preserves met=true", resp.json().get("met") == True)
check("Re-ingest preserves met_notes", resp.json().get("met_notes") == "Keep this note")


# ── Cleanup + Events delete ───────────────────────────────────────────────────

print("\n── Cleanup ──")

resp = r("delete", f"/api/events/{event_id}")
check("DELETE /api/events/{id} → 204", resp.status_code == 204)

resp = r("get", f"/api/events/{event_id}")
check("Event gone after delete → 404", resp.status_code == 404)

resp = r("get", f"/api/people/{person_id}")
check("People still exist after event delete (global)", resp.status_code == 200)


# ── Summary ───────────────────────────────────────────────────────────────────

print(f"\n{'─' * 50}")
if _failures:
    print(f"\033[91m{len(_failures)} test(s) failed:\033[0m")
    for f in _failures:
        print(f"  • {f}")
    sys.exit(1)
else:
    print(f"\033[92mAll tests passed.\033[0m")
