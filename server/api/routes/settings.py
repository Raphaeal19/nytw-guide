from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from server.api.deps import get_db, verify_ingest_secret
from server.db.models import ServiceConnection

router = APIRouter(prefix="/api/settings", tags=["settings"])


class ConnectionOut(BaseModel):
    service_name: str
    status: str
    last_connected_at: Optional[datetime] = None
    meta: Optional[dict] = None


class ConnectionUpdate(BaseModel):
    status: str
    meta: Optional[dict] = None


@router.get("/connections", response_model=list[ConnectionOut])
def list_connections(db: Session = Depends(get_db)):
    rows = db.query(ServiceConnection).all()
    return [
        ConnectionOut(
            service_name=r.service_name,
            status=r.status,
            last_connected_at=r.last_connected_at,
            meta=r.meta,
        )
        for r in rows
    ]


@router.get("/connections/{service}", response_model=ConnectionOut)
def get_connection(service: str, db: Session = Depends(get_db)):
    row = db.query(ServiceConnection).filter(
        ServiceConnection.service_name == service
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"No connection for '{service}'")
    return ConnectionOut(
        service_name=row.service_name,
        status=row.status,
        last_connected_at=row.last_connected_at,
        meta=row.meta,
    )


@router.post("/connections/{service}", response_model=ConnectionOut)
def upsert_connection(
    service: str,
    body: ConnectionUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(verify_ingest_secret),
):
    row = db.query(ServiceConnection).filter(
        ServiceConnection.service_name == service
    ).first()

    now = datetime.utcnow()
    if row:
        row.status = body.status
        row.meta = body.meta
        if body.status == "connected":
            row.last_connected_at = now
    else:
        row = ServiceConnection(
            service_name=service,
            status=body.status,
            last_connected_at=now if body.status == "connected" else None,
            meta=body.meta,
        )
        db.add(row)

    db.commit()
    db.refresh(row)
    return ConnectionOut(
        service_name=row.service_name,
        status=row.status,
        last_connected_at=row.last_connected_at,
        meta=row.meta,
    )
