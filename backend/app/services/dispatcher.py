import logging
from datetime import datetime

from sqlalchemy.orm import Session

from ..core.config import settings
from ..db import models
from .hub import hub
from .registry import registry
from .robot_parser import parse_output_xml

log = logging.getLogger(__name__)

CAPABILITY_FOR_TYPE = {
    "robot_run": "robot_execution",
    "run_command": "run_command",
}

ACTIVE_STATUSES = ("assigned", "running")


def task_event(task: models.Task) -> dict:
    return {
        "event": "task_update",
        "task": {
            "id": task.id,
            "type": task.type,
            "status": task.status,
            "worker_id": task.worker_id,
            "returncode": task.returncode,
            "error": task.error,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "finished_at": task.finished_at,
        },
    }


def _worker_busy(db: Session, worker_id: int) -> bool:
    return (
        db.query(models.Task)
        .filter(models.Task.worker_id == worker_id, models.Task.status.in_(ACTIVE_STATUSES))
        .count()
        > 0
    )


def worker_state(db: Session, worker: models.Worker) -> str:
    if not registry.is_online(worker.client_id):
        return "offline"
    return "busy" if _worker_busy(db, worker.id) else "online"


def _find_worker(db: Session, task: models.Task) -> models.Worker | None:
    capability = CAPABILITY_FOR_TYPE[task.type]
    if task.requested_worker_id:  # manual pick: only that worker qualifies
        worker = db.get(models.Worker, task.requested_worker_id)
        if (
            worker
            and registry.is_online(worker.client_id)
            and capability in (worker.capabilities or [])
            and not _worker_busy(db, worker.id)
        ):
            return worker
        return None
    for worker in db.query(models.Worker).all():
        if (
            registry.is_online(worker.client_id)
            and capability in (worker.capabilities or [])
            and not _worker_busy(db, worker.id)
        ):
            return worker
    return None


async def try_dispatch(db: Session) -> None:
    """Assign pending tasks to free capable workers, oldest first."""
    pending = (
        db.query(models.Task)
        .filter(models.Task.status == "pending")
        .order_by(models.Task.created_at)
        .all()
    )
    for task in pending:
        worker = _find_worker(db, task)
        if not worker:
            continue
        task.worker_id = worker.id
        task.status = "assigned"
        db.commit()
        sent = await registry.send(
            worker.client_id,
            {"type": "task", "task_id": task.id, "task_type": task.type, "payload": task.payload},
        )
        if not sent:
            task.status = "pending"
            task.worker_id = None
            db.commit()
            continue
        await hub.broadcast(task_event(task))


async def finish_task(
    db: Session,
    task: models.Task,
    status: str,
    returncode: int | None = None,
    error: str = "",
    output: str = "",
) -> None:
    task.status = status
    task.returncode = returncode
    task.error = error
    if output:
        task.output = output
    task.finished_at = datetime.utcnow()
    db.commit()

    if task.type == "robot_run" and status == "completed":
        artifact_dir = settings.artifacts_dir / str(task.id)
        xml = artifact_dir / "output.xml"
        if xml.exists():
            parse_output_xml(db, xml, task.id, str(artifact_dir))
            await hub.broadcast({"event": "result_created", "task_id": task.id})

    await hub.broadcast(task_event(task))
    await try_dispatch(db)  # worker freed up, pull the next pending task


async def fail_tasks_for_worker(db: Session, worker_id: int, reason: str) -> None:
    """Worker died mid-flight: fail its in-progress tasks."""
    tasks = (
        db.query(models.Task)
        .filter(models.Task.worker_id == worker_id, models.Task.status.in_(ACTIVE_STATUSES))
        .all()
    )
    for task in tasks:
        task.status = "failed"
        task.error = reason
        task.finished_at = datetime.utcnow()
        db.commit()
        await hub.broadcast(task_event(task))
