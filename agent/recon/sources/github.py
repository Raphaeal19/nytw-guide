"""GitHub via REST API — unauthenticated (60 req/hr)."""
import logging
import httpx

logger = logging.getLogger(__name__)

BASE = "https://api.github.com"
HEADERS = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}


async def scrape_github(github_handle: str | None, name: str = "") -> dict:
    handle = github_handle or await _search_handle(name)
    if not handle:
        return {}

    async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
        try:
            user_resp = await client.get(f"{BASE}/users/{handle}")
            if user_resp.status_code == 404:
                return {}
            user_resp.raise_for_status()
            user = user_resp.json()

            repos_resp = await client.get(
                f"{BASE}/users/{handle}/repos",
                params={"sort": "updated", "per_page": 10},
            )
            repos = repos_resp.json() if repos_resp.is_success else []

        except Exception as e:
            logger.warning(f"GitHub scrape failed for {handle}: {e}")
            return {}

    top_repos = [
        {
            "name": r["name"],
            "description": r.get("description"),
            "stars": r.get("stargazers_count", 0),
            "language": r.get("language"),
            "url": r.get("html_url"),
        }
        for r in repos
        if not r.get("fork")
    ][:5]

    return {
        "handle": handle,
        "profile_url": user.get("html_url"),
        "bio": user.get("bio"),
        "followers": user.get("followers", 0),
        "public_repos": user.get("public_repos", 0),
        "top_repos": top_repos,
        "repos_found": len(repos),
        "summary": _summarise(user, top_repos),
    }


async def _search_handle(name: str) -> str | None:
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=10) as client:
            resp = await client.get(f"{BASE}/search/users", params={"q": name, "per_page": 1})
            resp.raise_for_status()
            items = resp.json().get("items", [])
            return items[0]["login"] if items else None
    except Exception:
        return None


def _summarise(user: dict, repos: list[dict]) -> str:
    parts = []
    if user.get("bio"):
        parts.append(user["bio"])
    if repos:
        names = ", ".join(r["name"] for r in repos[:3])
        parts.append(f"Top repos: {names}.")
    followers = user.get("followers", 0)
    if followers > 100:
        parts.append(f"{followers:,} followers.")
    return " ".join(parts) if parts else ""
