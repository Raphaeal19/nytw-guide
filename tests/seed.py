#!/usr/bin/env python3
"""
Seed script — wipes events/people and repopulates with realistic data.
Run with the API server already running:
    python tests/seed.py
"""
import os, requests, sys

BASE   = os.environ.get("PI_URL", "http://localhost:8000")
SECRET = os.environ.get("INGEST_SECRET", "changeme")
H      = {"X-Ingest-Secret": SECRET, "Content-Type": "application/json"}

def api(method, path, **kw):
    r = getattr(requests, method)(f"{BASE}{path}", **kw)
    if not r.ok:
        print(f"ERROR {method.upper()} {path}: {r.status_code} {r.text[:200]}")
        sys.exit(1)
    return r.json()

# ── Wipe existing events (cascades to attendances) ───────────────────────────
print("Clearing existing events…")
for ev in api("get", "/api/events"):
    requests.delete(f"{BASE}/api/events/{ev['id']}")
print(f"  cleared.")

# ── Create events ─────────────────────────────────────────────────────────────
print("\nCreating events…")

e1 = api("post", "/api/events", json={
    "name": "SaaStr Annual 2025",
    "date_start": "2025-09-09",
    "date_end": "2025-09-11",
    "location": "San Mateo, CA",
    "tags": ["SaaS", "B2B", "Founders", "GTM"],
    "color": "#7F77DD",
})
e2 = api("post", "/api/events", json={
    "name": "AI Engineer World's Fair",
    "date_start": "2025-06-25",
    "date_end": "2025-06-26",
    "location": "San Francisco, CA",
    "tags": ["AI", "LLMs", "Infra", "Dev Tools"],
    "color": "#22c55e",
})
e3 = api("post", "/api/events", json={
    "name": "YC Demo Day W25",
    "date_start": "2025-03-25",
    "date_end": "2025-03-25",
    "location": "San Francisco, CA",
    "tags": ["Startups", "Seed", "Founders"],
    "color": "#f97316",
})
print(f"  created: {e1['name']}, {e2['name']}, {e3['name']}")

# ── People for SaaStr ─────────────────────────────────────────────────────────
SAAS_PEOPLE = [
    {
        "name": "Sarah Guo",
        "company": "Conviction",
        "role": "General Partner",
        "twitter_handle": "sarahguo",
        "linkedin_url": "https://linkedin.com/in/sarahguo",
        "bio_snapshot": "GP at Conviction, former a16z partner. One of the most active early-stage AI investors right now. Founded the Latent Space podcast community.",
        "talking_points": [
            {"text": "Said publicly she only writes checks into AI companies where the founding team has tried and failed at the problem before", "source": "Twitter, April 2025", "priority": 1},
            {"text": "Led the Series A in a stealth AI infra company focused on inference cost reduction", "source": "Web search, Feb 2025", "priority": 2},
            {"text": "Tweeted a thread on why 'AI wrappers' is a lazy take and unit economics matter more than moats in the current wave", "source": "Twitter, March 2025", "priority": 3},
        ],
        "recon_sources": {
            "twitter": {"posts_found": 45, "summary": "Very active — posts daily on AI investment thesis, portfolio company milestones, and pushback on popular takes. Engages heavily with founders."},
            "linkedin": {"posts_found": 4, "summary": "Less active than Twitter. Occasional thought leadership posts on founder-investor dynamics."},
            "github": {"repos_found": 0, "summary": ""},
            "web": {"summary": "Multiple podcast appearances (Latent Space, 20VC). Forbes 30 under 30 alum. Quoted in WSJ on AI investment cycle."},
        },
        "open_roles": [{"title": "EIR (Entrepreneur in Residence)", "dept": "Portfolio", "location": "SF", "url": "https://conviction.com/careers"}],
    },
    {
        "name": "Jason Lemkin",
        "company": "SaaStr",
        "role": "Founder & CEO",
        "twitter_handle": "jasonlk",
        "linkedin_url": "https://linkedin.com/in/jasonmlemkin",
        "bio_snapshot": "Founder of SaaStr, the world's largest B2B/SaaS community. Previously co-founded EchoSign (acquired by Adobe). Prolific Quora answerer and SaaS pundit.",
        "talking_points": [
            {"text": "Posted that ARR per employee of $200k is now the baseline bar for efficient SaaS — companies below that are 'zombies'", "source": "Twitter, May 2025", "priority": 1},
            {"text": "Running an experiment where SaaStr fund invests only in companies he's met at SaaStr events — said it's outperforming his other deal flow by 2x", "source": "Web search, March 2025", "priority": 2},
            {"text": "Publicly critical of founder-led sales dying too early — says most Series B CEOs stop selling 18 months too soon", "source": "LinkedIn, April 2025", "priority": 3},
        ],
        "recon_sources": {
            "twitter": {"posts_found": 200, "summary": "Extremely active. Multiple tweets per day. Mixes SaaS metrics hot takes with event promotion and portfolio company shoutouts."},
            "linkedin": {"posts_found": 30, "summary": "Long-form posts on SaaS benchmarks, fundraising trends, and GTM strategy. Very high engagement."},
            "web": {"summary": "Runs the SaaStr blog (millions of readers). Has a Quora following of 600k+. Quoted everywhere in B2B SaaS press."},
        },
        "open_roles": [],
    },
    {
        "name": "Zach DeWitt",
        "company": "Wing VC",
        "role": "Partner",
        "twitter_handle": "zachdewitt",
        "linkedin_url": "https://linkedin.com/in/zachdewitt",
        "bio_snapshot": "Partner at Wing VC focusing on enterprise software and AI infra. Former product manager at Google. Known for deep technical diligence on infrastructure plays.",
        "talking_points": [
            {"text": "Published a note arguing that vector databases are commoditizing and the real moat is in the orchestration layer above them", "source": "Wing VC blog, Feb 2025", "priority": 1},
            {"text": "Tweeted that most AI copilots will be deprecated in 18 months as capabilities get absorbed into core products", "source": "Twitter, March 2025", "priority": 2},
        ],
        "recon_sources": {
            "twitter": {"posts_found": 22, "summary": "Thoughtful posts on enterprise AI adoption, VC portfolio construction, and the occasional hot take on product strategy."},
            "linkedin": {"posts_found": 6, "summary": "Deal announcements and portfolio company updates. Less personal than his Twitter."},
            "web": {"summary": "Co-authored a piece on AI ROI in the enterprise with a16z. Speaks at SaaStr, Dreamforce, and Strata conferences."},
        },
        "open_roles": [],
    },
    {
        "name": "Erica Brescia",
        "company": "Redpoint Ventures",
        "role": "Managing Director",
        "linkedin_url": "https://linkedin.com/in/ericabrescia",
        "twitter_handle": "ericabrescia",
        "bio_snapshot": "MD at Redpoint. Former COO of GitHub (led through Microsoft acquisition). Deeply technical investor focused on dev tools, open source, and infra.",
        "talking_points": [
            {"text": "Wrote about how the GitHub acquisition playbook — preserve culture, don't rebrand, give autonomy — is being ignored by most acquirers today", "source": "LinkedIn, April 2025", "priority": 1},
            {"text": "Backed three open-source-first companies in Q1 2025, signaling a renewed conviction in OSS-led GTM after the HashiCorp debacle", "source": "Web search, March 2025", "priority": 2},
            {"text": "Said in a podcast that the best COOs she's seen all 'hold the chaos' — meaning they absorb organizational stress so founders can think long-term", "source": "Invest Like the Best, Jan 2025", "priority": 3},
        ],
        "recon_sources": {
            "linkedin": {"posts_found": 12, "summary": "Mix of portfolio company news, hiring posts for Redpoint, and longer reflections on leadership and company building."},
            "twitter": {"posts_found": 18, "summary": "Active but not daily. Open source ecosystem news, GitHub nostalgia, and dev tools landscape commentary."},
            "github": {"repos_found": 2, "summary": "A few public repos from her GitHub days — mostly internal tooling that got open-sourced."},
            "web": {"summary": "Frequent podcast guest. Co-chaired Open Source Summit. Often quoted in TechCrunch on enterprise OSS and infra investment."},
        },
        "open_roles": [{"title": "Principal", "dept": "Investment", "location": "SF", "url": "https://redpoint.com/careers"}],
    },
    {
        "name": "David Sacks",
        "company": "Craft Ventures",
        "role": "General Partner",
        "twitter_handle": "davidsacks",
        "linkedin_url": "https://linkedin.com/in/davidsacks",
        "bio_snapshot": "GP at Craft Ventures, PayPal Mafia founding member, former COO of Yammer. Co-host of the All-In podcast. Very online.",
        "talking_points": [
            {"text": "Posted a rant that SaaS multiples are 'mean-reverting to 2015 levels' and founders should stop using 2021 comps to justify valuations", "source": "Twitter, May 2025", "priority": 1},
            {"text": "Argued on All-In that AI will collapse most SaaS categories within 5 years — said he's avoiding investing in anything that's 'just software'", "source": "All-In Podcast, April 2025", "priority": 2},
        ],
        "recon_sources": {
            "twitter": {"posts_found": 180, "summary": "Extremely prolific. Posts on politics, AI, SaaS, startups. Heavy engagement, controversial takes. His AI skepticism threads regularly go viral."},
            "web": {"summary": "All-In Podcast co-host (top 10 tech podcast). Frequent Forbes/WSJ op-eds. Was briefly named as White House AI and Crypto Czar advisor."},
            "linkedin": {"posts_found": 2, "summary": "Barely uses LinkedIn. Occasional Craft Ventures announcements."},
        },
        "open_roles": [],
    },
    {
        "name": "Tomer London",
        "company": "Gusto",
        "role": "Co-Founder & CPO",
        "linkedin_url": "https://linkedin.com/in/tomerlondon",
        "github_handle": "tomerlondon",
        "bio_snapshot": "Co-founder and CPO of Gusto. Built the payroll product from scratch as the first engineer. Has scaled Gusto to 300k+ small business customers.",
        "talking_points": [
            {"text": "Shared that Gusto's biggest product mistake was building too many features for enterprise before nailing the SMB core — said it cost them 18 months", "source": "SaaStr Talk, 2024", "priority": 1},
            {"text": "Tweeted about their AI payroll anomaly detection that saved customers $4M in payroll errors in Q1 alone", "source": "LinkedIn, March 2025", "priority": 2},
        ],
        "recon_sources": {
            "linkedin": {"posts_found": 8, "summary": "Thoughtful product management and startup leadership posts. High signal-to-noise ratio."},
            "github": {"repos_found": 12, "summary": "Active committer early in Gusto's history. Some open-source contributions to Ruby and React ecosystem."},
            "web": {"summary": "Regular speaker at SaaStr, Mind the Product. Multiple interviews on product-led growth and building for SMBs."},
        },
        "open_roles": [
            {"title": "Staff Product Manager", "dept": "Core Product", "location": "Denver / Remote", "url": "https://gusto.com/careers"},
            {"title": "Senior Software Engineer", "dept": "Payroll Infra", "location": "Remote", "url": "https://gusto.com/careers"},
        ],
    },
]

# ── People for AI Engineer World's Fair ───────────────────────────────────────
AI_PEOPLE = [
    {
        "name": "Swyx",
        "company": "Latent Space",
        "role": "Founder",
        "twitter_handle": "swyx",
        "github_handle": "sw-yx",
        "linkedin_url": "https://linkedin.com/in/swyx",
        "bio_snapshot": "Creator of the Latent Space podcast and community. Former developer advocate at AWS and Netlify. Coined 'learn in public.' Currently building the AI Engineer community.",
        "talking_points": [
            {"text": "Wrote 'The Rise of the AI Engineer' — the most-shared essay on what the AI engineering role actually is vs ML engineer", "source": "Latent Space blog, 2024", "priority": 1},
            {"text": "Building a new product that helps AI engineers share and discover prompts — said it's the missing layer between GitHub and Hugging Face", "source": "Twitter, April 2025", "priority": 2},
            {"text": "Openly documents his product failures on Twitter — last week posted a post-mortem on a feature that 40 people tried and zero retained", "source": "Twitter, May 2025", "priority": 3},
        ],
        "recon_sources": {
            "twitter": {"posts_found": 300, "summary": "Daily posting. Mix of AI ecosystem news, personal learning, community building, and startup updates. Very engaged with replies."},
            "github": {"repos_found": 45, "summary": "Very active. Multiple popular repos including 'awesome-chatgpt-prompts' forks and developer tooling. Strong open source presence."},
            "web": {"summary": "Latent Space podcast (top AI podcast). Frequent conference speaker. 'Learn in public' philosophy widely cited in dev education circles."},
            "linkedin": {"posts_found": 3, "summary": "Rare posts. Mostly cross-posts from Twitter."},
        },
        "open_roles": [],
    },
    {
        "name": "Shreya Rajpal",
        "company": "Guardrails AI",
        "role": "CEO & Co-Founder",
        "twitter_handle": "shreyarajpal",
        "github_handle": "shreya-rajpal",
        "bio_snapshot": "CEO of Guardrails AI, the open-source framework for adding safety and structure to LLM outputs. Former ML engineer at Apple and Predibase.",
        "talking_points": [
            {"text": "Said in a talk that 80% of LLM production failures she sees are output format issues, not model quality — validation is the unsexy problem nobody wants to solve", "source": "AI Engineer Summit talk, 2024", "priority": 1},
            {"text": "Guardrails just hit 4M monthly PyPI downloads — fastest-growing OSS AI safety tool by downloads in 2025", "source": "Twitter, April 2025", "priority": 2},
        ],
        "recon_sources": {
            "github": {"repos_found": 8, "summary": "guardrails-ai org has 7k+ stars. Very active in the repo — responds to issues personally. Strong community engagement."},
            "twitter": {"posts_found": 35, "summary": "Regular posts on LLM reliability, structured outputs, and OSS community updates."},
            "linkedin": {"posts_found": 5, "summary": "Company updates and fundraising announcements."},
        },
        "open_roles": [{"title": "Staff Engineer", "dept": "Core", "location": "Remote", "url": "https://guardrailsai.com/careers"}],
    },
    {
        "name": "Harrison Chase",
        "company": "LangChain",
        "role": "CEO & Co-Founder",
        "twitter_handle": "hwchase17",
        "github_handle": "hwchase17",
        "linkedin_url": "https://linkedin.com/in/harrison-chase-961587118",
        "bio_snapshot": "Creator of LangChain, the most widely used LLM application framework. Built LangChain in a weekend in Nov 2022, now runs a company of 70+ people. Previously at Robust Intelligence.",
        "talking_points": [
            {"text": "Announced LangGraph Cloud — managed infrastructure for running LangGraph agents at scale. Said it's their answer to the 'yes but can it run in prod?' question", "source": "Twitter, March 2025", "priority": 1},
            {"text": "Shared that 80% of LangChain users are building RAG pipelines but only 20% ever ship to production — said the eval gap is the biggest blocker", "source": "AI Engineer Summit, 2024", "priority": 2},
            {"text": "Responded to the 'LangChain is too complex' criticism by saying they deliberately chose breadth over simplicity to capture the learning surface of the ecosystem", "source": "Twitter thread, Feb 2025", "priority": 3},
        ],
        "recon_sources": {
            "github": {"repos_found": 15, "summary": "Most active committer on langchain and langgraph repos. Reviews PRs daily. The repo has 90k+ stars."},
            "twitter": {"posts_found": 120, "summary": "Daily posts on LangChain ecosystem, agent patterns, RAG techniques, and the occasional competitive positioning post."},
            "linkedin": {"posts_found": 8, "summary": "Company announcements and funding news. Less personal than Twitter."},
            "web": {"summary": "Most-interviewed person in the AI dev tools space. Profiled in WSJ, TechCrunch, Wired. Forbes AI 50 2024."},
        },
        "open_roles": [
            {"title": "Senior Software Engineer", "dept": "LangGraph", "location": "SF / Remote", "url": "https://langchain.com/careers"},
            {"title": "Developer Advocate", "dept": "DevRel", "location": "Remote", "url": "https://langchain.com/careers"},
        ],
    },
    {
        "name": "Simon Willison",
        "company": "Datasette",
        "role": "Creator & Independent Developer",
        "twitter_handle": "simonw",
        "github_handle": "simonw",
        "bio_snapshot": "Created Django (with Adrian Holovaty) and Datasette. Runs one of the most-read technical blogs on AI and open source tooling. Prolific open-source contributor.",
        "talking_points": [
            {"text": "Published a post arguing that 'AI-assisted coding is the most important productivity improvement in software development since version control'", "source": "simonwillison.net, April 2025", "priority": 1},
            {"text": "Built and released 47 open-source tools in 2024 alone — all AI-assisted. Running a live experiment in public on what LLM-accelerated solo dev looks like", "source": "GitHub + blog, 2024", "priority": 2},
            {"text": "Wrote a detailed breakdown of every prompt injection attack pattern he's found in the wild — the definitive reference on the topic", "source": "simonwillison.net, March 2025", "priority": 3},
        ],
        "recon_sources": {
            "github": {"repos_found": 200, "summary": "Extraordinarily prolific. Datasette, sqlite-utils, llm CLI tool, and hundreds of smaller projects. Among the top 100 most-starred GitHub users."},
            "twitter": {"posts_found": 400, "summary": "Multiple posts per day. Technical, thoughtful, often first to publish analysis on new model releases. Huge following in the open-source and AI space."},
            "web": {"summary": "simonwillison.net is one of the most-cited technical blogs. Django creator credit gives him massive credibility in the Python ecosystem."},
        },
        "open_roles": [],
    },
]

# ── People for YC Demo Day ─────────────────────────────────────────────────────
YC_PEOPLE = [
    {
        "name": "Garry Tan",
        "company": "Y Combinator",
        "role": "President & CEO",
        "twitter_handle": "garrytan",
        "linkedin_url": "https://linkedin.com/in/garrytan",
        "bio_snapshot": "President of Y Combinator. Formerly founder of Posterous, partner at Initialized Capital. Took over YC in 2023 and has been aggressively vocal about SF policy and the startup ecosystem.",
        "talking_points": [
            {"text": "Said YC is now accepting more non-technical founding teams than ever — thinks the AI tools gap has closed enough that this works", "source": "Twitter, April 2025", "priority": 1},
            {"text": "Publicly feuded with SF Board of Supervisors on Twitter — got personally involved in three local ballot measures. Polarizing but effective.", "source": "Web search, 2024-2025", "priority": 2},
            {"text": "Announced YC will fund 10 AI safety companies in W25 batch regardless of revenue — said it's the 'portfolio hedge' they owe the world", "source": "Twitter, March 2025", "priority": 3},
        ],
        "recon_sources": {
            "twitter": {"posts_found": 250, "summary": "Very active and often controversial. Mix of startup advice, SF politics, AI hype-checking, and portfolio news. Responds to criticism publicly."},
            "linkedin": {"posts_found": 6, "summary": "Less active. Mostly YC batch announcements and thought leadership reposts."},
            "web": {"summary": "Profiled in every major tech outlet post-YC appointment. His tweets regularly trend in tech circles."},
        },
        "open_roles": [],
    },
    {
        "name": "Diana Hu",
        "company": "Niantic",
        "role": "Co-Founder & CTO",
        "linkedin_url": "https://linkedin.com/in/dianahy",
        "twitter_handle": "dianahu",
        "bio_snapshot": "CTO of Niantic (Pokemon Go). Previously co-founded Escher Reality (AR multiplayer SDK), acquired by Niantic in 2018. Deep AR/spatial computing expertise.",
        "talking_points": [
            {"text": "Gave a talk arguing that spatial computing's real unlock isn't Apple Vision Pro but sub-$300 glasses — said they're 18 months away from a product in this range", "source": "TED talk, March 2025", "priority": 1},
            {"text": "Niantic's new platform lets indie developers build AR games with multiplayer in under a week — she shipped the first demo live on stage", "source": "GDC 2025", "priority": 2},
        ],
        "recon_sources": {
            "linkedin": {"posts_found": 7, "summary": "Technical and leadership-focused posts. AR industry commentary and Niantic product updates."},
            "twitter": {"posts_found": 14, "summary": "Less frequent but thoughtful. AR/spatial computing commentary and conference live-tweeting."},
            "web": {"summary": "Forbes 30 Under 30. Frequent speaker at AR/VR conferences. Profiled in MIT Tech Review on the future of spatial computing."},
        },
        "open_roles": [{"title": "Senior AR Engineer", "dept": "Platform", "location": "SF", "url": "https://niantic.com/careers"}],
    },
]

# ── Ingest all people ─────────────────────────────────────────────────────────
print("\nIngesting people…")

r = api("post", "/api/ingest", json={"event_id": e1["id"], "people": SAAS_PEOPLE}, headers=H)
print(f"  SaaStr: {r['upserted']} people")

r = api("post", "/api/ingest", json={"event_id": e2["id"], "people": AI_PEOPLE}, headers=H)
print(f"  AI Engineer: {r['upserted']} people")

r = api("post", "/api/ingest", json={"event_id": e3["id"], "people": YC_PEOPLE}, headers=H)
print(f"  YC Demo Day: {r['upserted']} people")

# ── Mark a few as met with notes ──────────────────────────────────────────────
print("\nMarking some people as met…")

saas_people = api("get", f"/api/events/{e1['id']}/people")
by_name = {p["name"]: p for p in saas_people}

if "Sarah Guo" in by_name:
    att_id = by_name["Sarah Guo"]["attendance_id"]
    api("post", f"/api/attendance/{att_id}/met", json={
        "met": True,
        "notes": "Talked about AI infra unit economics and her portfolio company doing inference cost reduction. She's interested in seeing our agent pipeline benchmarks. Follow up with the numbers.",
    })
    print("  ✓ Sarah Guo")

if "Tomer London" in by_name:
    att_id = by_name["Tomer London"]["attendance_id"]
    api("post", f"/api/attendance/{att_id}/met", json={
        "met": True,
        "notes": "Discussed the AI payroll anomaly detection feature. He mentioned they're open to partnerships with companies building on top of Gusto's API.",
    })
    print("  ✓ Tomer London")

ai_people = api("get", f"/api/events/{e2['id']}/people")
by_name_ai = {p["name"]: p for p in ai_people}

if "Swyx" in by_name_ai:
    att_id = by_name_ai["Swyx"]["attendance_id"]
    api("post", f"/api/attendance/{att_id}/met", json={
        "met": True,
        "notes": "Long conversation about the AI Engineer community he's building. He's looking for sponsors for the next summit. Also genuinely curious about how we're using LangGraph.",
    })
    print("  ✓ Swyx")

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n── Done ──")
events = api("get", "/api/events")
for ev in events:
    print(f"  {ev['name']}: {ev['people_count']} people, {ev['met_count']} met")
