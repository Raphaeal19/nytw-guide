import logging
import math
from io import BytesIO

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

_app = None


def _get_app():
    global _app
    if _app is None:
        from insightface.app import FaceAnalysis
        _app = FaceAnalysis(
            name="buffalo_s",
            providers=["CPUExecutionProvider"],
        )
        _app.prepare(ctx_id=0, det_size=(320, 320))
    return _app


def extract_embedding(image_bytes: bytes) -> list[float] | None:
    try:
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        arr = np.array(img)
        faces = _get_app().get(arr)
        if not faces:
            logger.info("No face detected in image")
            return None
        face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        return face.embedding.tolist()
    except Exception:
        logger.exception("Face embedding extraction failed")
        return None


def compute_similarity(emb1: list[float], emb2: list[float]) -> float:
    dot = sum(a * b for a, b in zip(emb1, emb2))
    norm1 = math.sqrt(sum(a * a for a in emb1))
    norm2 = math.sqrt(sum(b * b for b in emb2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)
