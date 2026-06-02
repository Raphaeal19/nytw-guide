from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from server.api.deps import get_db
from server.api.routes.people import _attendance_with_person
from server.db.models import Person, EventAttendance
from server.face.embedder import extract_embedding, compute_similarity

router = APIRouter(tags=["identify"])

_MATCH_THRESHOLD = 0.45


@router.post("/api/events/{event_id}/identify")
async def identify_person(
    event_id: UUID,
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    contents = await image.read()
    query_embedding = extract_embedding(contents)

    if query_embedding is None:
        return {"match": None, "confidence": 0.0, "error": "No face detected in image"}

    attendances = (
        db.query(EventAttendance)
        .options(joinedload(EventAttendance.person))
        .join(Person)
        .filter(
            EventAttendance.event_id == event_id,
            Person.face_embedding.isnot(None),
        )
        .all()
    )

    best_match = None
    best_score = -1.0

    for att in attendances:
        score = compute_similarity(query_embedding, att.person.face_embedding)
        if score > best_score:
            best_score = score
            best_match = att

    if best_match and best_score >= _MATCH_THRESHOLD:
        return {
            "match": _attendance_with_person(best_match),
            "confidence": round(best_score, 3),
        }

    return {"match": None, "confidence": round(best_score, 3) if best_score > 0 else 0.0}
