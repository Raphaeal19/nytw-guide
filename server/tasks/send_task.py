import logging
from datetime import datetime
from server.tasks.celery_app import celery_app
from server.db.database import SessionLocal
from server.db.models import EventAttendance

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_outreach_task(self, attendance_id: str, channel: str, message: str):
    db = SessionLocal()
    try:
        att = db.get(EventAttendance, attendance_id)
        if not att:
            logger.error(f"Attendance {attendance_id} not found")
            return

        if att.outreach_sent:
            logger.warning(f"Outreach already sent for {attendance_id} — aborting")
            return

        if not att.met:
            logger.warning(f"Attendance {attendance_id} not marked as met — aborting")
            return

        if channel == "linkedin":
            from server.outreach.linkedin import send_linkedin_dm
            send_linkedin_dm(att.person.linkedin_url, message)
        elif channel == "email":
            from server.outreach.gmail import send_gmail
            send_gmail(att.person.email, message)
        elif channel == "twitter":
            from server.outreach.twitter import send_twitter_dm
            send_twitter_dm(att.person.twitter_handle, message)
        else:
            raise ValueError(f"Unknown channel: {channel}")

        att.outreach_sent = True
        att.outreach_channel = channel
        att.outreach_draft = message
        att.outreach_sent_at = datetime.utcnow()
        db.commit()

    except Exception as exc:
        db.rollback()
        raise self.retry(exc=exc)
    finally:
        db.close()
