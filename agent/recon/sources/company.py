"""Company page scraper — about page + open roles via Playwright."""
import logging
import re

logger = logging.getLogger(__name__)

CAREERS_SLUGS = ["/careers", "/jobs", "/work-with-us", "/join", "/join-us", "/hiring"]


async def scrape_company(company_name: str, company_site: str | None = None) -> dict:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.warning("playwright not installed — skipping company scrape")
        return {}

    site = company_site or await _find_site(company_name)
    if not site:
        return {}

    about_text = ""
    open_roles: list[dict] = []

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            page.set_default_timeout(15_000)

            # About page
            try:
                await page.goto(site, wait_until="domcontentloaded")
                about_text = (await page.inner_text("main, body"))[:2000]
            except Exception as e:
                logger.warning(f"Company about page failed ({site}): {e}")

            # Careers page
            for slug in CAREERS_SLUGS:
                careers_url = site.rstrip("/") + slug
                try:
                    resp = await page.goto(careers_url, wait_until="domcontentloaded")
                    if resp and resp.status < 400:
                        text = await page.inner_text("main, body")
                        open_roles = _extract_roles(text, careers_url)
                        break
                except Exception:
                    continue

            await browser.close()
    except Exception as e:
        logger.warning(f"Company scrape failed for {company_name}: {e}")
        return {}

    return {
        "site": site,
        "about_snippet": about_text[:500],
        "open_roles": open_roles[:10],
        "summary": _summarise(company_name, about_text, open_roles),
    }


async def _find_site(company_name: str) -> str | None:
    import httpx
    from agent.config import settings

    if not settings.serper_api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": settings.serper_api_key},
                json={"q": f"{company_name} official website", "num": 1},
            )
            items = resp.json().get("organic", [])
            if items:
                url = items[0].get("link", "")
                # Strip to root domain
                m = re.match(r"(https?://[^/]+)", url)
                return m.group(1) if m else None
    except Exception:
        return None


def _extract_roles(text: str, source_url: str) -> list[dict]:
    roles: list[dict] = []
    # Very rough heuristic — real implementation would parse structured job listings
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    job_keywords = {"engineer", "manager", "designer", "analyst", "lead", "director",
                    "scientist", "developer", "recruiter", "product", "marketing"}
    for line in lines:
        if (
            len(line) > 10
            and len(line) < 100
            and any(kw in line.lower() for kw in job_keywords)
            and not line.lower().startswith(("we ", "our ", "the ", "you ", "join "))
        ):
            roles.append({"title": line, "url": source_url})
        if len(roles) >= 10:
            break
    return roles


def _summarise(company: str, about: str, roles: list[dict]) -> str:
    parts = []
    if about:
        parts.append(about[:300])
    if roles:
        parts.append(f"{len(roles)} open roles found.")
    return " ".join(parts) if parts else ""
