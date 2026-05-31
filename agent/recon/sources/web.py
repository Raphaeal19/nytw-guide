"""Web search — DuckDuckGo (free, no key) with optional Serper upgrade."""
import logging

from agent.config import settings

logger = logging.getLogger(__name__)


async def scrape_web(name: str, company: str, role: str = "") -> dict:
    queries = [
        f'"{name}" "{company}"',
        f'"{name}" site:linkedin.com/in',
        f'"{name}" site:x.com OR site:twitter.com',
        f'"{name}" site:github.com',
        f'"{name}" {company} interview OR talk OR podcast',
    ]

    if settings.serper_api_key:
        all_results = await _search_serper(queries)
    else:
        all_results = await _search_ddg(queries)

    if not all_results:
        return {}

    seen: set[str] = set()
    unique = []
    for r in all_results:
        url = r.get("url", "")
        if url and url not in seen:
            seen.add(url)
            unique.append(r)

    linkedin_url = next((r["url"] for r in unique if "linkedin.com/in/" in r["url"]), None)
    twitter_handle = None
    github_handle = None
    for r in unique:
        url = r["url"]
        if ("twitter.com/" in url or "x.com/" in url) and not twitter_handle:
            parts = url.rstrip("/").split("/")
            handle = parts[-1].lstrip("@") if parts else ""
            if handle and not any(c in handle for c in "?#="):
                twitter_handle = handle
        if "github.com/" in url and not github_handle:
            parts = url.rstrip("/").split("/")
            if len(parts) >= 4:
                handle = parts[3]
                if handle and not any(c in handle for c in "?#="):
                    github_handle = handle

    logger.info(f"web handles — linkedin={linkedin_url} twitter={twitter_handle} github={github_handle}")
    logger.debug(f"web urls: {[r['url'] for r in unique[:5]]}")

    return {
        "results": unique[:10],
        "linkedin_url": linkedin_url,
        "twitter_handle": twitter_handle,
        "github_handle": github_handle,
        "summary": f"Found {len(unique)} web results for {name}.",
    }


async def _search_ddg(queries: list[str]) -> list[dict]:
    try:
        from ddgs import DDGS
    except ImportError:
        logger.warning("ddgs not installed — run: pip install ddgs")
        return []

    results: list[dict] = []
    with DDGS() as ddgs:
        for q in queries:
            try:
                for r in ddgs.text(q, max_results=5):
                    results.append({
                        "title": r.get("title"),
                        "url": r.get("href", ""),
                        "snippet": r.get("body"),
                    })
            except Exception as e:
                logger.warning(f"DDG query failed ({q!r}): {e}")
    return results


async def _search_serper(queries: list[str]) -> list[dict]:
    import httpx

    results: list[dict] = []
    async with httpx.AsyncClient(timeout=15) as client:
        for q in queries:
            try:
                resp = await client.post(
                    "https://google.serper.dev/search",
                    headers={"X-API-KEY": settings.serper_api_key},
                    json={"q": q, "num": 5},
                )
                resp.raise_for_status()
                for r in resp.json().get("organic", []):
                    results.append({
                        "title": r.get("title"),
                        "url": r.get("link", ""),
                        "snippet": r.get("snippet"),
                    })
            except Exception as e:
                logger.warning(f"Serper query failed ({q!r}): {e}")
    return results
