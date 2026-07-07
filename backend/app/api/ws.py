import base64
import json
import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..core.config import settings
from ..core.security import decode_token, verify_password
from ..db import models
from ..db.session import SessionLocal
from ..services import dispatcher
from ..services.hub import hub
from ..services.registry import registry

log = logging.getLogger(__name__)
router = APIRouter()

MAX_OUTPUT_CHARS = 1_000_000  # per task; keeps a runaway command from bloating the DB


def worker_event(db, worker: models.Worker) -> dict:
    return {
        "event": "worker_status",
        "worker": {
            "id": worker.id,
            "client_id": worker.client_id,
            "status": dispatcher.worker_state(db, worker),
            "capabilities": worker.capabilities or [],
        },
    }


@router.websocket("/ws/worker")
async def worker_socket(ws: WebSocket):
    await ws.accept()

    # --- Handshake: first message must be a valid registration ---
    try:
        raw = await ws.receive_text()
        reg = json.loads(raw)
    except Exception:
        await ws.close(code=4400)
        return

    client_id = reg.get("client_id", "")
    token = reg.get("token", "")
    with SessionLocal() as db:
        worker = db.query(models.Worker).filter_by(client_id=client_id).first()
        if not worker or not token or not verify_password(token, worker.token_hash):
            log.warning("Worker auth failed for client_id=%r", client_id)
            await ws.close(code=4401)
            return
        if registry.is_online(client_id):
            log.warning("Duplicate connection for %r rejected", client_id)
            await ws.close(code=4409)
            return

        worker.hostname = reg.get("hostname", "")
        worker.ip_address = ws.client.host if ws.client else ""
        worker.os = reg.get("os", "")
        worker.capabilities = reg.get("capabilities", [])
        worker.status = "online"
        worker.last_heartbeat = datetime.utcnow()
        db.commit()
        worker_id = worker.id

        registry.add(client_id, ws)
        await ws.send_text(json.dumps({"type": "registered"}))
        log.info("Worker %s connected: %s", client_id, worker.capabilities)
        await hub.broadcast(worker_event(db, worker))
        await dispatcher.try_dispatch(db)

    output_buffers: dict[int, list[str]] = {}
    output_sizes: dict[int, int] = {}
    upload: dict | None = None  # in-flight artifact upload

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            mtype = msg.get("type")

            if mtype == "heartbeat":
                with SessionLocal() as db:
                    db.query(models.Worker).filter_by(id=worker_id).update(
                        {"last_heartbeat": datetime.utcnow(), "status": "online"}
                    )
                    db.commit()

            elif mtype == "task_status":
                with SessionLocal() as db:
                    task = db.get(models.Task, msg.get("task_id"))
                    if task and msg.get("status") == "running":
                        task.status = "running"
                        task.started_at = datetime.utcnow()
                        db.commit()
                        await hub.broadcast(dispatcher.task_event(task))

            elif mtype == "output":
                task_id = msg.get("task_id")
                data = msg.get("data", "")
                if output_sizes.get(task_id, 0) < MAX_OUTPUT_CHARS:
                    output_buffers.setdefault(task_id, []).append(data)
                    output_sizes[task_id] = output_sizes.get(task_id, 0) + len(data)
                await hub.broadcast({"event": "task_output", "task_id": task_id, "data": data})

            elif mtype == "file_begin":
                task_id = int(msg["task_id"])
                filename = Path(msg["filename"]).name  # strip any path components
                target_dir = settings.artifacts_dir / str(task_id)
                target_dir.mkdir(parents=True, exist_ok=True)
                upload = {"handle": open(target_dir / filename, "wb")}

            elif mtype == "file_chunk" and upload:
                upload["handle"].write(base64.b64decode(msg["data"]))

            elif mtype == "file_end" and upload:
                upload["handle"].close()
                upload = None

            elif mtype == "task_result":
                task_id = msg.get("task_id")
                with SessionLocal() as db:
                    task = db.get(models.Task, task_id)
                    if task:
                        await dispatcher.finish_task(
                            db,
                            task,
                            status=msg.get("status", "failed"),
                            returncode=msg.get("returncode"),
                            error=msg.get("error", ""),
                            output="".join(output_buffers.pop(task_id, [])),
                        )
                output_sizes.pop(task_id, None)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.error("Worker %s connection error: %s", client_id, e)
    finally:
        if upload:
            upload["handle"].close()
        registry.remove(client_id)
        with SessionLocal() as db:
            worker = db.get(models.Worker, worker_id)
            if worker:
                worker.status = "offline"
                db.commit()
                await dispatcher.fail_tasks_for_worker(db, worker_id, "Worker disconnected")
                await hub.broadcast(worker_event(db, worker))
        log.info("Worker %s disconnected", client_id)


@router.websocket("/ws/ui")
async def ui_socket(ws: WebSocket, token: str = ""):
    username = decode_token(token)
    if not username:
        await ws.close(code=4401)
        return
    with SessionLocal() as db:
        user = db.query(models.User).filter_by(username=username).first()
        if not user or not user.is_active:
            await ws.close(code=4401)
            return

    await ws.accept()
    hub.add(ws)
    try:
        while True:
            await ws.receive_text()  # keepalive pings from the client; content ignored
    except WebSocketDisconnect:
        pass
    finally:
        hub.remove(ws)
