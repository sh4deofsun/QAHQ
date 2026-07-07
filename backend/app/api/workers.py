import base64
import secrets

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.permissions import Perm
from ..core.security import hash_password
from ..db import models
from ..db.session import get_db
from ..services.dispatcher import worker_state
from ..services.registry import registry
from .deps import require

router = APIRouter(prefix="/api/workers", tags=["workers"])


class WorkerCreate(BaseModel):
    client_id: str


def serialize(db: Session, w: models.Worker) -> dict:
    return {
        "id": w.id,
        "client_id": w.client_id,
        "hostname": w.hostname,
        "ip_address": w.ip_address,
        "os": w.os,
        "capabilities": w.capabilities or [],
        "status": worker_state(db, w),
        "last_heartbeat": w.last_heartbeat,
        "created_at": w.created_at,
    }


@router.get("", dependencies=[Depends(require(Perm.WORKER_VIEW))])
def list_workers(db: Session = Depends(get_db)):
    return [serialize(db, w) for w in db.query(models.Worker).order_by(models.Worker.client_id)]


@router.post("", dependencies=[Depends(require(Perm.WORKER_MANAGE))], status_code=201)
def register_worker(body: WorkerCreate, db: Session = Depends(get_db)):
    if db.query(models.Worker).filter_by(client_id=body.client_id).first():
        raise HTTPException(status_code=409, detail="client_id already registered")
    token = secrets.token_urlsafe(32)
    worker = models.Worker(client_id=body.client_id, token_hash=hash_password(token))
    db.add(worker)
    db.commit()
    db.refresh(worker)
    # Token is shown exactly once; only its hash is stored.
    return {"worker": serialize(db, worker), "token": token}


@router.post("/{worker_id}/token", dependencies=[Depends(require(Perm.WORKER_MANAGE))])
async def regenerate_token(worker_id: int, db: Session = Depends(get_db)):
    worker = db.get(models.Worker, worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    token = secrets.token_urlsafe(32)
    worker.token_hash = hash_password(token)
    db.commit()
    ws = registry.connections.get(worker.client_id)
    if ws:  # old token no longer valid — drop the live session
        await ws.close(code=4401)
    return {"token": token}


@router.post("/{worker_id}/files", dependencies=[Depends(require(Perm.WORKER_MANAGE))])
async def send_file_to_worker(worker_id: int, file: UploadFile, db: Session = Depends(get_db)):
    """Push a file (test script, config) to the worker's incoming directory."""
    worker = db.get(models.Worker, worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    content = await file.read()
    # ponytail: single-frame base64, chunk when files outgrow WS frame limits
    sent = await registry.send(
        worker.client_id,
        {"type": "file", "filename": file.filename, "data": base64.b64encode(content).decode()},
    )
    if not sent:
        raise HTTPException(status_code=409, detail="Worker is not online")
    return {"status": "sent", "filename": file.filename}


@router.delete("/{worker_id}", dependencies=[Depends(require(Perm.WORKER_MANAGE))], status_code=204)
async def delete_worker(worker_id: int, db: Session = Depends(get_db)):
    worker = db.get(models.Worker, worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    ws = registry.connections.get(worker.client_id)
    if ws:
        await ws.close(code=4401)
    db.query(models.Task).filter_by(worker_id=worker.id).update({"worker_id": None})
    db.delete(worker)
    db.commit()
