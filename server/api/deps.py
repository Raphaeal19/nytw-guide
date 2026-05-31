from typing import Generator
from fastapi import Header, HTTPException
from sqlalchemy.orm import Session
from server.db.database import SessionLocal
from server.config import settings


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_ingest_secret(x_ingest_secret: str = Header(...)) -> None:
    if x_ingest_secret != settings.pi_api_secret:
        raise HTTPException(status_code=401, detail="Invalid ingest secret")
