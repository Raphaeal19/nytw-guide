from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from server.api.deps import get_db
from server.db.models import Person, EventAttendance

router = APIRouter(tags=["people"])


class PersonUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    location: Optional[str] = None
    photo_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_handle: Optional[str] = None
    github_handle: Optional[str] = None
    instagram_handle: Optional[str] = None
    personal_site: Optional[str] = None
    email: Optional[str] = None


def _attendance_with_person(att: EventAttendance) -> dict:
    p = att.person
    return {
        "attendance_id": str(att.id),
        "person_id": str(p.id),
        "name": p.name,
        "company": p.company,
        "role": p.role,
        "location": p.location,
        "photo_url": p.photo_url,
        "linkedin_url": p.linkedin_url,
        "twitter_handle": p.twitter_handle,
        "github_handle": p.github_handle,
        "bio_snapshot": p.bio_snapshot,
        "talking_points": p.talking_points,
        "recon_sources": p.recon_sources,
        "agent_ran_at": p.agent_ran_at,
        "open_roles": att.open_roles,
        "met": att.met,
        "met_at": att.met_at,
        "met_notes": att.met_notes,
        "selfie_url": att.selfie_url,
        "outreach_sent": att.outreach_sent,
        "outreach_channel": att.outreach_channel,
        "outreach_draft": att.outreach_draft,
        "outreach_sent_at": att.outreach_sent_at,
    }


@router.get("/api/events/{event_id}/people")
def list_people_for_event(
    event_id: UUID,
    met: Optional[bool] = Query(None),
    q: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = (
        db.query(EventAttendance)
        .options(joinedload(EventAttendance.person))
        .filter(EventAttendance.event_id == event_id)
    )
    if met is not None:
        query = query.filter(EventAttendance.met == met)

    attendances = query.all()

    results = [_attendance_with_person(a) for a in attendances]

    if q:
        q_lower = q.lower()
        results = [
            r for r in results
            if q_lower in (r["name"] or "").lower()
            or q_lower in (r["company"] or "").lower()
            or q_lower in (r["role"] or "").lower()
        ]

    return results


@router.get("/api/people/{person_id}")
def get_person(person_id: UUID, db: Session = Depends(get_db)):
    person = db.get(Person, person_id)
    if not person:
        raise HTTPException(404, "Person not found")
    return person


@router.get("/api/attendance/{attendance_id}")
def get_attendance(attendance_id: UUID, db: Session = Depends(get_db)):
    att = db.get(EventAttendance, attendance_id)
    if not att:
        raise HTTPException(404, "Attendance not found")
    return att


@router.patch("/api/people/{person_id}")
def update_person(person_id: UUID, body: PersonUpdate, db: Session = Depends(get_db)):
    person = db.get(Person, person_id)
    if not person:
        raise HTTPException(404, "Person not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(person, field, value)
    db.commit()
    db.refresh(person)
    return person
