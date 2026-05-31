from sqlalchemy import (
    Column, String, Boolean, Text, Date, DateTime,
    ForeignKey, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from uuid import uuid4
from datetime import datetime
from .database import Base


class Event(Base):
    __tablename__ = "events"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name        = Column(String, nullable=False)
    date_start  = Column(Date)
    date_end    = Column(Date)
    location    = Column(String)
    description = Column(Text)
    tags        = Column(ARRAY(String))
    color       = Column(String)
    created_at  = Column(DateTime, default=datetime.utcnow)

    attendances = relationship("EventAttendance", back_populates="event",
                               cascade="all, delete")


class Person(Base):
    """Global person record. Created once, reused across all events."""
    __tablename__ = "people"

    __table_args__ = (
        UniqueConstraint("name", "company", name="uq_person_name_company"),
    )

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    name             = Column(String, nullable=False)
    company          = Column(String)
    role             = Column(String)
    location         = Column(String)
    photo_url        = Column(String)

    linkedin_url     = Column(String)
    twitter_handle   = Column(String)
    github_handle    = Column(String)
    instagram_handle = Column(String)
    personal_site    = Column(String)
    email            = Column(String)

    bio_snapshot     = Column(Text)
    talking_points   = Column(JSONB)
    recon_sources    = Column(JSONB)
    raw_intel        = Column(JSONB)
    agent_ran_at     = Column(DateTime)

    created_at       = Column(DateTime, default=datetime.utcnow)

    attendances = relationship("EventAttendance", back_populates="person")


class EventAttendance(Base):
    """Per-event state for a person. One row per (person, event) pair."""
    __tablename__ = "event_attendances"

    __table_args__ = (
        UniqueConstraint("person_id", "event_id", name="uq_person_event"),
    )

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    person_id = Column(UUID(as_uuid=True), ForeignKey("people.id"), nullable=False)
    event_id  = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)

    open_roles = Column(JSONB)

    met        = Column(Boolean, default=False)
    met_at     = Column(DateTime)
    met_notes  = Column(Text)

    outreach_sent    = Column(Boolean, default=False)
    outreach_channel = Column(String)
    outreach_draft   = Column(Text)
    outreach_sent_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)

    person = relationship("Person", back_populates="attendances")
    event  = relationship("Event",  back_populates="attendances")
