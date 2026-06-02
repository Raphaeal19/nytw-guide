import logging
import httpx
from sqlalchemy.orm import Session
from server.db.models import Person, EventAttendance
from server.face.embedder import extract_embedding

logger = logging.getLogger(__name__)


def precompute_embeddings_for_event(event_id: str, db: Session) -> int:
    attendances = (
        db.query(EventAttendance)
        .join(Person)
        .filter(
            EventAttendance.event_id == event_id,
            Person.photo_url.isnot(None),
            Person.face_embedding.is_(None),
        )
        .all()
    )

    computed = 0
    for att in attendances:
        person = att.person
        try:
            resp = httpx.get(person.photo_url, timeout=15, follow_redirects=True)
            if resp.status_code != 200:
                continue
            embedding = extract_embedding(resp.content)
            if embedding:
                person.face_embedding = embedding
                db.commit()
                computed += 1
                logger.info(f"Computed embedding for {person.name}")
        except Exception:
            logger.exception(f"Failed to compute embedding for {person.name}")

    return computed
