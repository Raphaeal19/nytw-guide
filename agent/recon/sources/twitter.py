"""Twitter/X — public timeline via Playwright with saved session."""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _find_cookie_file() -> str | None:
    path = Path(__file__).parent.parent.parent / "twitter_auth.json"
    return str(path) if path.exists() else None


async def scrape_twitter(twitter_handle: str | None) -> dict:
    if not twitter_handle:
        return {}

    cookie_file = _find_cookie_file()
    if not cookie_file:
        logger.warning("twitter_auth.json not found — run: python setup_linkedin_auth.py")
        return {}

    handle = twitter_handle.lstrip("@")

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.warning("playwright not installed — skipping Twitter")
        return {}

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                storage_state=cookie_file,
            )
            page = await context.new_page()
            page.set_default_timeout(20_000)

            await page.goto(f"https://x.com/{handle}", wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

            tweets = await page.locator('[data-testid="tweetText"]').all_text_contents()
            bio_el = page.locator('[data-testid="UserDescription"]')
            bio = (await bio_el.text_content() or "").strip() if await bio_el.count() > 0 else ""

            await browser.close()

        if not tweets and not bio:
            return {}

        return {
            "handle": handle,
            "bio": bio,
            "posts_found": len(tweets),
            "recent_posts": [t[:200] for t in tweets[:10]],
            "summary": _summarise(handle, bio, tweets),
        }

    except Exception as e:
        logger.warning(f"Twitter scrape failed for @{handle}: {e}")
        return {}


def _summarise(handle: str, bio: str, tweets: list[str]) -> str:
    parts = []
    if bio:
        parts.append(bio[:150])
    if tweets:
        parts.append(f"{len(tweets)} recent posts found.")
    return " ".join(parts)
