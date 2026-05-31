"""Instagram via instaloader — public profiles only."""
import logging

logger = logging.getLogger(__name__)


async def scrape_instagram(instagram_handle: str | None, name: str = "") -> dict:
    if not instagram_handle:
        return {}

    try:
        import instaloader
    except ImportError:
        logger.warning("instaloader not installed — skipping Instagram")
        return {}

    try:
        L = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_comments=False,
            save_metadata=False,
            quiet=True,
        )
        profile = instaloader.Profile.from_username(L.context, instagram_handle)

        recent_captions: list[str] = []
        for post in profile.get_posts():
            if len(recent_captions) >= 5:
                break
            if post.caption:
                recent_captions.append(post.caption[:200])

        return {
            "handle": instagram_handle,
            "followers": profile.followers,
            "bio": profile.biography,
            "posts_found": min(len(recent_captions), 5),
            "recent_captions": recent_captions,
            "summary": _summarise(profile, recent_captions),
        }

    except Exception as e:
        logger.warning(f"Instagram scrape failed for {instagram_handle}: {e}")
        return {}


def _summarise(profile, captions: list[str]) -> str:
    parts = []
    if profile.biography:
        parts.append(profile.biography[:150])
    if profile.followers > 1000:
        parts.append(f"{profile.followers:,} followers.")
    if captions:
        parts.append(f"{len(captions)} recent posts found.")
    return " ".join(parts)
