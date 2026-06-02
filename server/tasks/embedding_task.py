import logging
import httpx
from server.tasks.celery_app import celery_app
from server.db.database import SessionLocal
from server.db.models import Person
from server.face.embedder import extract_embedding

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def compute_embedding_task(self, person_id: str):
    db = SessionLocal()
    try:
        person = db.get(Person, person_id)
        if not person:
            logger.error(f"Person {person_id} not found")
            return
        if person.face_embedding:
            return
        if not person.photo_url:
            return

        resp = httpx.get(person.photo_url, timeout=15, follow_redirects=True)
        if resp.status_code != 200:
            logger.warning(f"Failed to download photo for {person.name}: HTTP {resp.status_code}")
            return

        embedding = extract_embedding(resp.content)
        if embedding:
            person.face_embedding = embedding
            db.commit()
            logger.info(f"Computed embedding for {person.name}")
        else:
            logger.info(f"No face detected for {person.name}")

    except Exception as exc:
        db.rollback()
        raise self.retry(exc=exc)
    finally:
        db.close()
