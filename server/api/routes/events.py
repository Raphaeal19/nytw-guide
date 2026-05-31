from uuid import UUID
from typing import Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from pydantic import BaseModel
from server.api.deps import get_db
from server.db.models import Event, EventAttendance

router = APIRouter(prefix="/api/events", tags=["events"])


class EventCreate(BaseModel):
    name: str
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    location: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list[str]] = None
    color: Optional[str] = None


class EventUpdate(BaseModel):
    name: Optional[str] = None
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    location: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list[str]] = None
    color: Optional[str] = None


@router.get("")
def list_events(db: Session = Depends(get_db)):
    events = db.query(Event).order_by(Event.date_start.desc()).all()
    result = []
    for ev in events:
        people_count = db.query(func.count(EventAttendance.id)).filter(
            EventAttendance.event_id == ev.id
        ).scalar()
        met_count = db.query(func.count(EventAttendance.id)).filter(
            EventAttendance.event_id == ev.id,
            EventAttendance.met == True,
        ).scalar()
        result.append({
            "id": str(ev.id),
            "name": ev.name,
            "date_start": ev.date_start,
            "date_end": ev.date_end,
            "location": ev.location,
            "tags": ev.tags,
            "color": ev.color,
            "people_count": people_count,
            "met_count": met_count,
        })
    return result


@router.post("", status_code=201)
def create_event(body: EventCreate, db: Session = Depends(get_db)):
    ev = Event(**body.model_dump())
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return {"id": str(ev.id), **body.model_dump()}


@router.get("/{event_id}")
def get_event(event_id: UUID, db: Session = Depends(get_db)):
    ev = db.get(Event, event_id)
    if not ev:
        raise HTTPException(404, "Event not found")
    return ev


@router.patch("/{event_id}")
def update_event(event_id: UUID, body: EventUpdate, db: Session = Depends(get_db)):
    ev = db.get(Event, event_id)
    if not ev:
        raise HTTPException(404, "Event not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(ev, field, value)
    db.commit()
    db.refresh(ev)
    return ev


@router.delete("/{event_id}", status_code=204)
def delete_event(event_id: UUID, db: Session = Depends(get_db)):
    ev = db.get(Event, event_id)
    if not ev:
        raise HTTPException(404, "Event not found")
    db.delete(ev)
    db.commit()
