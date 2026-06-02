from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from server.api.deps import get_db
from server.db.models import EventAttendance

router = APIRouter(prefix="/api/outreach", tags=["outreach"])


class DraftRequest(BaseModel):
    attendance_id: UUID
    channel: str  # "linkedin" | "email" | "twitter"
    extra_context: Optional[str] = None


class SendRequest(BaseModel):
    attendance_id: UUID
    channel: str
    message: str


class PolishRequest(BaseModel):
    raw_notes: str
    person_name: str


@router.post("/draft")
def draft_outreach(body: DraftRequest, db: Session = Depends(get_db)):
    att = db.get(EventAttendance, body.attendance_id)
    if not att:
        raise HTTPException(404, "Attendance not found")
    if not att.met:
        raise HTTPException(400, "Cannot draft outreach for someone not yet met")

    from server.drafter.drafter import draft_message
    draft = draft_message(att, body.channel, body.extra_context)

    att.outreach_draft = draft
    att.outreach_channel = body.channel
    db.commit()

    return {"draft": draft}


@router.post("/send")
def send_outreach(body: SendRequest, db: Session = Depends(get_db)):
    att = db.get(EventAttendance, body.attendance_id)
    if not att:
        raise HTTPException(404, "Attendance not found")
    if not att.met:
        raise HTTPException(400, "Cannot send outreach for someone not yet met")
    if att.outreach_sent:
        raise HTTPException(409, "Outreach already sent")

    from server.tasks.send_task import send_outreach_task
    task = send_outreach_task.delay(
        str(body.attendance_id), body.channel, body.message
    )

    return {"task_id": task.id, "status": "queued"}


@router.post("/polish-notes")
def polish_notes_endpoint(body: PolishRequest):
    from server.drafter.drafter import polish_notes
    polished = polish_notes(body.raw_notes, body.person_name)
    return {"polished": polished}


@router.get("/status/{task_id}")
def outreach_status(task_id: str):
    from server.tasks.celery_app import celery_app
    result = celery_app.AsyncResult(task_id)

    if result.state == "SUCCESS":
        return {"status": "sent"}
    elif result.state == "FAILURE":
        return {"status": "failed", "error": str(result.result)}
    else:
        return {"status": "queued"}
