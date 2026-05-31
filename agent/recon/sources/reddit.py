"""Reddit via public JSON API — no credentials needed."""
import logging

import httpx

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}
SEARCH_URL = "https://old.reddit.com/search.json"


async def scrape_reddit(name: str, company: str) -> dict:
    queries = [f'"{name}"', f'"{name}" "{company}"']
    posts: list[dict] = []
    seen: set[str] = set()

    async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
        for q in queries:
            try:
                resp = await client.get(
                    SEARCH_URL,
                    params={"q": q, "sort": "relevance", "t": "year", "limit": 10},
                )
                resp.raise_for_status()
                items = resp.json().get("data", {}).get("children", [])
                for item in items:
                    d = item.get("data", {})
                    pid = d.get("id")
                    if not pid or pid in seen:
                        continue
                    seen.add(pid)
                    posts.append({
                        "title": d.get("title"),
                        "subreddit": d.get("subreddit"),
                        "score": d.get("score", 0),
                        "url": f"https://reddit.com{d.get('permalink', '')}",
                        "text": (d.get("selftext") or "")[:300] or None,
                    })
            except Exception as e:
                logger.debug(f"Reddit search failed ({q!r}): {e}")

    if not posts:
        return {}

    return {
        "posts_found": len(posts),
        "posts": posts[:10],
        "summary": f"Found {len(posts)} Reddit posts mentioning {name}.",
    }
