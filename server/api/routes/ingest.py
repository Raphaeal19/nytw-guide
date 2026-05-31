from uuid import UUID
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from pydantic import BaseModel
from server.api.deps import get_db, verify_ingest_secret
from server.db.models import Person, EventAttendance

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


class OpenRole(BaseModel):
    title: str
    dept: Optional[str] = None
    location: Optional[str] = None
    url: Optional[str] = None


class TalkingPoint(BaseModel):
    text: str
    source: str
    priority: int


class PersonProfile(BaseModel):
    name: str
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
    bio_snapshot: Optional[str] = None
    talking_points: Optional[list[TalkingPoint]] = None
    recon_sources: Optional[dict] = None
    raw_intel: Optional[dict] = None
    open_roles: Optional[list[OpenRole]] = None


class IngestRequest(BaseModel):
    event_id: UUID
    people: list[PersonProfile]


@router.post("")
def ingest(
    body: IngestRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_ingest_secret),
):
    upserted = 0
    for profile in body.people:
        person_data = {
            "name": profile.name,
            "company": profile.company,
            "role": profile.role,
            "location": profile.location,
            "photo_url": profile.photo_url,
            "linkedin_url": profile.linkedin_url,
            "twitter_handle": profile.twitter_handle,
            "github_handle": profile.github_handle,
            "instagram_handle": profile.instagram_handle,
            "personal_site": profile.personal_site,
            "email": profile.email,
            "bio_snapshot": profile.bio_snapshot,
            "talking_points": [tp.model_dump() for tp in profile.talking_points] if profile.talking_points else None,
            "recon_sources": profile.recon_sources,
            "raw_intel": profile.raw_intel,
            "agent_ran_at": datetime.utcnow(),
        }

        # Look up by name first so company changes (NULL → real value) don't create duplicates
        existing = db.query(Person).filter(
            func.lower(Person.name) == profile.name.lower()
        ).first()

        if existing:
            for field, value in person_data.items():
                if value is not None:
                    setattr(existing, field, value)
            person_id = existing.id
        else:
            stmt = (
                insert(Person)
                .values(**person_data)
                .on_conflict_do_update(
                    constraint="uq_person_name_company",
                    set_={k: v for k, v in person_data.items() if k not in ("name", "company")},
                )
                .returning(Person.id)
            )
            result = db.execute(stmt)
            person_id = result.scalar_one()

        open_roles_data = [r.model_dump() for r in profile.open_roles] if profile.open_roles else None

        att_stmt = (
            insert(EventAttendance)
            .values(
                person_id=person_id,
                event_id=body.event_id,
                open_roles=open_roles_data,
            )
            .on_conflict_do_update(
                constraint="uq_person_event",
                # Never overwrite user-generated fields (met, notes, outreach)
                set_={"open_roles": open_roles_data},
            )
        )
        db.execute(att_stmt)
        upserted += 1

    db.commit()
    return {"upserted": upserted}
