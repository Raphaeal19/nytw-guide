"""Face matching stub — Phase 15 implementation."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def match_face(image_path: str, candidates: list[dict]) -> dict | None:
    """
    Phase 15: match a captured face against known attendee profile photos.
    Returns the best-matching candidate dict, or None if no match above threshold.
    """
    logger.warning("Face matching not yet implemented (Phase 15 stub)")
    return None


async def extract_embedding(image_path: str) -> list[float] | None:
    """Phase 15: extract ArcFace embedding from an image file."""
    logger.warning("Face embedding not yet implemented (Phase 15 stub)")
    return None
