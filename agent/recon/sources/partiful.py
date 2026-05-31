"""
Partiful scraper.

Two public entry points:
  scrape_all_my_events()       — open the feed, find every event, scrape all guest lists
  scrape_partiful_event(url)   — scrape a single event URL

Run `python agent/setup_partiful_auth.py` once before using either.
"""
from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

_PROFILE_DIR = Path(__file__).parent.parent.parent / "partiful_profile"

# ── JavaScript helpers ────────────────────────────────────────────────────────

# Find event links on the Partiful feed page
_FIND_EVENTS_JS = """
() => {
    const seen = new Set();
    const events = [];
    document.querySelectorAll('a[href*="/e/"]').forEach(a => {
        const m = (a.href || '').match(/partiful\\.com\\/e\\/([A-Za-z0-9_-]+)/);
        if (!m) return;
        const url = 'https://partiful.com/e/' + m[1];
        if (seen.has(url)) return;
        seen.add(url);
        // Walk up to find the nearest text that looks like an event name
        let name = (a.innerText || '').trim();
        if (!name || name.length < 3) {
            let el = a.parentElement;
            for (let i = 0; i < 5 && el; i++, el = el.parentElement) {
                const t = (el.innerText || '').split('\\n')[0].trim();
                if (t.length > 3 && t.length < 120) { name = t; break; }
            }
        }
        events.push({ url, name: name || url });
    });
    return events;
}
"""

# Find person-name-shaped text on an event page
_FIND_NAMES_JS = """
() => {
    const nameRe = /^[A-ZÀ-ÖÀ-ž][a-zà-žXx''-]+(?:[ \\-][A-ZÀ-ÖÀ-ž][a-zà-žXx''-]+)+$/;
    const BLOCKLIST = new Set([
        'Tech Week','Guest List','Restricted Access','The List','View All',
        'See All','Going','Not Going','Maybe','Invited','Attending',
        'Full Name','First Name','Last Name','Add Guest','New York',
    ]);
    const results = [];
    const seen = new Set();
    document.querySelectorAll('p, span, div, h3, h4, button, a').forEach(el => {
        const text = (el.innerText || '').trim();
        if (!nameRe.test(text)) return;
        if (seen.has(text) || text.length < 4 || text.length > 50) return;
        if (text.includes('\\n')) return;
        if (BLOCKLIST.has(text)) return;
        const words = text.split(/\\s+/);
        if (words.length < 2 || words.length > 4) return;
        const childText = Array.from(el.children).map(c => (c.innerText||'').trim()).join('');
        if (childText && childText === text) return;
        seen.add(text);
        results.push({ text, tag: el.tagName.toLowerCase() });
    });
    return results;
}
"""

# Extract social links from the currently-visible profile sheet
_EXTRACT_SOCIAL_JS = """
() => {
    const d = { instagram: null, twitter: null, linkedin: null, photo: null, bio: null };
    document.querySelectorAll('a[href]').forEach(a => {
        const h = a.href || '';
        if (!d.instagram) { const m = h.match(/instagram\\.com\\/(\\w[\\w.]{0,29})/); if (m) d.instagram = m[1]; }
        if (!d.twitter) {
            const m = h.match(/(?:twitter|x)\\.com\\/(\\w{1,15})/);
            if (m && !['home','share','intent','i','oauth','en','search'].includes(m[1].toLowerCase()))
                d.twitter = m[1];
        }
        if (!d.linkedin) { const m = h.match(/linkedin\\.com\\/in\\/([\\w-]+)/); if (m) d.linkedin = m[1]; }
    });
    for (const img of document.querySelectorAll('img')) {
        const s = img.src || '';
        if (!s || s.startsWith('data:')) continue;
        const w = img.naturalWidth || img.width || 0;
        const h2 = img.naturalHeight || img.height || 0;
        if (w < 30 || h2 < 30) continue;
        if (w > 4 * h2 || h2 > 4 * w) continue;
        d.photo = s; break;
    }
    for (const el of document.querySelectorAll('p, [class*="bio"], [class*="about"], [class*="desc"]')) {
        const t = (el.innerText || '').trim();
        if (t.length > 20 && t.length < 400 && !/^[A-Z][a-z]+ [A-Z]/.test(t)) { d.bio = t; break; }
    }
    return d;
}
"""


# ── Public API ────────────────────────────────────────────────────────────────

async def scrape_all_my_events(names_only: bool = True) -> list[dict]:
    """
    Open the Partiful feed, discover all events, and scrape the guest list for each.
    Uses a single browser session for efficiency.

    Returns list of event dicts (same shape as scrape_partiful_event).
    names_only=True (default) skips click-through — fast, names without social handles.
    """
    if not _profile_exists():
        return []

    results = []
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            context = await _open_context(p)
            page = context.pages[0] if context.pages else await context.new_page()
            page.set_default_timeout(15_000)

            # Auth check via the feed page
            logger.info("Loading Partiful feed...")
            await page.goto("https://partiful.com", wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

            if _is_login_page(page.url):
                logger.warning("Partiful session expired — re-run setup_partiful_auth.py")
                await context.close()
                return []

            # Scroll feed to surface all event cards
            for _ in range(4):
                await page.keyboard.press("End")
                await page.wait_for_timeout(600)
            await page.keyboard.press("Home")
            await page.wait_for_timeout(400)

            event_links = await page.evaluate(_FIND_EVENTS_JS)
            logger.info(f"Found {len(event_links)} event links on feed")

            for ev in event_links:
                url = ev["url"]
                hint_name = ev.get("name", "")
                logger.info(f"Scraping: {hint_name or url}")
                result = await _scrape_event_page(page, url, names_only=names_only)
                if result:
                    # If the page title is better than the feed hint, use it
                    if not result.get("event_name") and hint_name:
                        result["event_name"] = hint_name
                    if result.get("guests"):
                        results.append(result)
                    else:
                        logger.info(f"  No guests found — skipping")

            await context.close()

    except Exception as e:
        logger.error(f"scrape_all_my_events error: {e}", exc_info=True)

    return results


async def scrape_partiful_event(url: str, names_only: bool = False) -> dict:
    """
    Scrape a single Partiful event URL.

    names_only=True skips click-through — fast, returns names without social handles.
    """
    if not _profile_exists():
        return {}

    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            context = await _open_context(p)
            page = context.pages[0] if context.pages else await context.new_page()
            page.set_default_timeout(15_000)

            result = await _scrape_event_page(page, url, names_only=names_only)
            await context.close()
            return result or {}

    except Exception as e:
        logger.error(f"scrape_partiful_event error: {e}", exc_info=True)
        return {}


# ── Internal: single-page scraping (reused by both public functions) ──────────

async def _scrape_event_page(page, url: str, names_only: bool) -> dict | None:
    """Navigate to an event URL and extract metadata + guest list."""
    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_timeout(3000)

    if _is_login_page(page.url):
        logger.warning("Partiful session expired — re-run setup_partiful_auth.py")
        return None

    meta = await _extract_event_meta(page)
    logger.info(f"  Event meta: {meta}")

    await _try_expand_guest_list(page)
    guests = await _extract_guests(page, names_only=names_only)
    logger.info(f"  Guests: {len(guests)}")

    return {**meta, "guests": guests}


# ── Browser context ───────────────────────────────────────────────────────────

async def _open_context(p):
    """Launch Chrome with the persistent Partiful profile."""
    try:
        return await p.chromium.launch_persistent_context(
            str(_PROFILE_DIR), channel="chrome", headless=False,
        )
    except Exception:
        logger.warning("System Chrome not found, falling back to bundled Chromium")
        return await p.chromium.launch_persistent_context(
            str(_PROFILE_DIR), headless=False,
        )


def _profile_exists() -> bool:
    if not _PROFILE_DIR.exists() or not any(_PROFILE_DIR.iterdir()):
        logger.warning("Partiful profile not found — run: python agent/setup_partiful_auth.py")
        return False
    return True


def _is_login_page(url: str) -> bool:
    return any(s in url for s in ("/login", "/sign-in", "/verify", "/welcome"))


# ── Event metadata ────────────────────────────────────────────────────────────

async def _extract_event_meta(page) -> dict:
    meta = {"event_name": "", "date": "", "location": ""}

    for sel in ["h1", "[data-testid='event-title']"]:
        el = page.locator(sel).first
        if await el.count() > 0:
            text = (await el.text_content() or "").strip()
            if text and text.lower() not in ("partiful",):
                meta["event_name"] = text.split(" | ")[0].strip()
                break

    for sel in ["time", "[datetime]", "[data-testid='event-date']"]:
        el = page.locator(sel).first
        if await el.count() > 0:
            text = (await el.text_content() or "").strip()
            if text:
                meta["date"] = text
                break

    return meta


# ── Guest list loading ────────────────────────────────────────────────────────

async def _try_expand_guest_list(page) -> None:
    for sel in [
        "text=/see all/i", "text=/view all/i", "text=/show all/i",
        "text=/all guests/i", "button:has-text('going')",
        "[role='button']:has-text('going')",
    ]:
        try:
            btn = page.locator(sel).first
            if await btn.count() > 0:
                await btn.click()
                await page.wait_for_timeout(1200)
                logger.info(f"  Expanded guest list via: {sel}")
                break
        except Exception:
            pass

    for _ in range(8):
        await page.keyboard.press("End")
        await page.wait_for_timeout(350)
    await page.keyboard.press("Home")
    await page.wait_for_timeout(300)


# ── Guest extraction ──────────────────────────────────────────────────────────

async def _extract_guests(page, names_only: bool) -> list[dict]:
    candidates = await page.evaluate(_FIND_NAMES_JS)
    if not candidates:
        logger.warning("No names found — dumping page text for debugging")
        await _dump_page_text(page)
        return []

    seen: set[str] = set()
    names: list[str] = []
    for c in candidates:
        n = c["text"].strip()
        if n not in seen:
            seen.add(n)
            names.append(n)

    redacted = sum(1 for n in names if _is_redacted(n))
    if redacted > len(names) * 0.3:
        logger.warning(
            f"  {redacted}/{len(names)} names appear redacted — "
            "re-run setup_partiful_auth.py if session expired"
        )

    if names_only:
        return [_empty_guest(n) for n in names]

    guests: list[dict] = []
    for name in names:
        guests.append(await _click_one_guest(page, name))
    return guests


async def _click_one_guest(page, name: str) -> dict:
    try:
        return await asyncio.wait_for(_click_and_extract(page, name), timeout=6.0)
    except asyncio.TimeoutError:
        logger.debug(f"Timeout on {name}")
        try:
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.3)
        except Exception:
            pass
        return _empty_guest(name)
    except Exception as e:
        logger.debug(f"Error on {name}: {e}")
        return _empty_guest(name)


async def _click_and_extract(page, name: str) -> dict:
    el = page.get_by_text(name, exact=True).first
    if await el.count() == 0:
        return _empty_guest(name)

    await el.scroll_into_view_if_needed()
    await el.click()
    await page.wait_for_timeout(700)

    social = await page.evaluate(_EXTRACT_SOCIAL_JS)

    dismissed = False
    for sel in [
        "button[aria-label='Close']", "button[aria-label='close']",
        "[data-testid='close-button']", "[data-testid='dismiss']",
        "button:has-text('×')", "button:has-text('✕')", "button:has-text('Done')",
    ]:
        btn = page.locator(sel).first
        if await btn.count() > 0:
            await btn.click()
            await page.wait_for_timeout(300)
            dismissed = True
            break
    if not dismissed:
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(300)

    return {
        "name": name,
        "instagram": social.get("instagram"),
        "twitter": social.get("twitter"),
        "linkedin_url": (
            f"https://linkedin.com/in/{social['linkedin']}"
            if social.get("linkedin") else None
        ),
        "photo_url": social.get("photo"),
        "bio": social.get("bio"),
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _dump_page_text(page) -> None:
    try:
        text = await page.inner_text("body")
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", prefix="partiful_debug_", delete=False
        ) as f:
            f.write(text)
            logger.warning(f"Page text saved to: {f.name}")
    except Exception:
        pass


def _is_redacted(name: str) -> bool:
    xs = sum(1 for c in name if c == 'x')
    return xs > len(name) * 0.4


def _empty_guest(name: str) -> dict:
    return {
        "name": name,
        "instagram": None,
        "twitter": None,
        "linkedin_url": None,
        "photo_url": None,
        "bio": None,
    }
