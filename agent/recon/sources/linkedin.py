"""LinkedIn scraper — Playwright with saved session (run setup_linkedin_auth.py first)."""
import asyncio
import logging
import random
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_last_call_at: float = 0.0
_MIN_DELAY = 15.0
_JITTER = 10.0


async def _throttle():
    global _last_call_at
    gap = time.monotonic() - _last_call_at
    wait = _MIN_DELAY + random.uniform(0, _JITTER) - gap
    if wait > 0:
        await asyncio.sleep(wait)
    _last_call_at = time.monotonic()


async def scrape_linkedin(linkedin_url: str | None, name: str = "") -> dict:
    if not linkedin_url and not name:
        return {}

    cookie_file = _find_cookie_file()
    if not cookie_file:
        logger.warning("linkedin_auth.json not found — run: python setup_linkedin_auth.py")
        return {}

    logger.info(f"LinkedIn scraping: {linkedin_url or name}")
    await _throttle()
    return await _scrape_via_playwright(linkedin_url, name, cookie_file)


async def _scrape_via_playwright(url: str | None, name: str, cookie_file: str) -> dict:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.warning("playwright not installed")
        return {}

    target_url = url or f"https://www.linkedin.com/search/results/people/?keywords={name.replace(' ', '%20')}"

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                storage_state=cookie_file,
            )
            page = await context.new_page()
            page.set_default_timeout(20_000)

            await page.goto(target_url, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

            # Bail if redirected to login wall
            if "linkedin.com/login" in page.url or "authwall" in page.url:
                logger.warning("LinkedIn session expired — re-run setup_linkedin_auth.py")
                await browser.close()
                return {}

            # If landed on search results, navigate to first profile
            if "search/results" in page.url:
                first = page.locator(".entity-result__title-text a, .app-aware-link").first
                if await first.count() > 0:
                    href = await first.get_attribute("href")
                    if href and "/in/" in href:
                        await page.goto(href, wait_until="domcontentloaded")
                        await page.wait_for_timeout(2000)

            profile_url = page.url
            slug = profile_url.rstrip("/").split("/in/")[-1].split("/")[0] if "/in/" in profile_url else ""

            # Try multiple headline selectors — LinkedIn changes these frequently
            headline = ""
            for sel in [
                ".text-body-medium.break-words",
                "h2.top-card-layout__headline",
                ".pv-text-details__left-panel .text-body-medium",
                ".top-card__subline-item",
            ]:
                el = page.locator(sel).first
                if await el.count() > 0:
                    text = (await el.text_content() or "").strip()
                    if text:
                        headline = text
                        break

            # Try multiple about/summary selectors
            summary = ""
            for sel in [
                ".pv-about-section .pv-about__summary-text",
                "#about ~ * .visually-hidden",
                ".core-section-container__content .pv-shared-text-with-see-more",
            ]:
                el = page.locator(sel).first
                if await el.count() > 0:
                    text = (await el.text_content() or "").strip()
                    if text:
                        summary = text[:500]
                        break

            # Fallback: pull top lines from main body text
            if not headline and not summary:
                try:
                    body = await page.inner_text("main")
                    lines = [l.strip() for l in body.splitlines() if len(l.strip()) > 20]
                    summary = "\n".join(lines[:6])[:500]
                except Exception:
                    pass

            logger.info(f"LinkedIn result — headline={headline!r} summary_len={len(summary)} url={profile_url}")
            await browser.close()

        if not headline and not summary:
            return {}

        return {
            "handle": slug,
            "profile_url": profile_url,
            "headline": headline,
            "summary": summary,
            "summary_text": _summarise(headline, summary),
        }

    except Exception as e:
        logger.warning(f"LinkedIn scrape failed for {url or name}: {e}")
        return {}


def _find_cookie_file() -> str | None:
    path = Path(__file__).parent.parent.parent / "linkedin_auth.json"
    return str(path) if path.exists() else None


def _summarise(headline: str, summary: str) -> str:
    parts = [p for p in [headline, summary[:200] if summary else ""] if p]
    return " ".join(parts)
