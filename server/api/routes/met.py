from uuid import UUID
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from server.api.deps import get_db
from server.db.models import EventAttendance
from server.tasks.celery_app import celery_app

router = APIRouter(prefix="/api/attendance", tags=["met"])


class MetUpdate(BaseModel):
    met: bool
    notes: Optional[str] = None


@router.post("/{attendance_id}/met")
def toggle_met(attendance_id: UUID, body: MetUpdate, db: Session = Depends(get_db)):
    att = db.get(EventAttendance, attendance_id)
    if not att:
        raise HTTPException(404, "Attendance not found")

    att.met = body.met
    if body.notes is not None:
        att.met_notes = body.notes
    if body.met and not att.met_at:
        att.met_at = datetime.utcnow()

    db.commit()
    db.refresh(att)

    return {
        "attendance_id": str(att.id),
        "met": att.met,
        "met_at": att.met_at,
        "met_notes": att.met_notes,
    }
