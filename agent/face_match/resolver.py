"""Face-to-attendee resolver stub — Phase 15 implementation."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def resolve_person_from_photo(image_path: str, event_id: str) -> dict | None:
    """
    Phase 15: given a photo and event, identify which attendee it is.
    Fetches attendee photos from Pi, runs face matching, returns Person dict or None.
    """
    logger.warning("Face resolver not yet implemented (Phase 15 stub)")
    return None
