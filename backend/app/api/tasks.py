from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, model_validator
from sqlalchemy.orm import Session

from ..core.permissions import Perm
from ..db import models
from ..db.session import get_db
from ..services import dispatcher
from ..services.hub import hub
from ..services.registry import registry
from .deps import get_current_user, require

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class RobotSource(BaseModel):
    git_url: str = ""
    git_ref: str = ""
    path: str = ""  # suite path inside the repo, or absolute path on the worker

    @model_validator(mode="after")
    def check(self):
        if not self.git_url and not self.path:
            raise ValueError("Either git_url or a worker path is required")
        return self


class RobotOptions(BaseModel):
    include_tags: list[str] = []
    exclude_tags: list[str] = []
    variables: dict[str, str] = {}


class TaskCreate(BaseModel):
    type: Literal["robot_run", "run_command"]
    worker_id: int | None = None  # None = auto dispatch
    command: str = ""  # run_command
    source: RobotSource | None = None  # robot_run
    options: RobotOptions = RobotOptions()

    @model_validator(mode="after")
    def check(self):
        if self.type == "run_command" and not self.command.strip():
            raise ValueError("command is required for run_command")
        if self.type == "robot_run" and self.source is None:
            raise ValueError("source is required for robot_run")
        return self


PERM_FOR_TYPE = {"robot_run": Perm.TASK_CREATE_ROBOT, "run_command": Perm.TASK_CREATE_COMMAND}


def serialize(task: models.Task, include_output: bool = False) -> dict:
    data = {
        "id": task.id,
        "type": task.type,
        "status": task.status,
        "payload": task.payload,
        "worker_id": task.worker_id,
        "worker_client_id": task.worker.client_id if task.worker else None,
        "returncode": task.returncode,
        "error": task.error,
        "created_at": task.created_at,
        "started_at": task.started_at,
        "finished_at": task.finished_at,
    }
    if include_output:
        data["output"] = task.output
    return data


@router.post("", status_code=201)
async def create_task(
    body: TaskCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    perm = PERM_FOR_TYPE[body.type]
    if perm.value not in user.permissions:
        raise HTTPException(status_code=403, detail=f"Missing permission: {perm.value}")

    if body.worker_id and not db.get(models.Worker, body.worker_id):
        raise HTTPException(status_code=404, detail="Worker not found")

    if body.type == "run_command":
        payload = {"command": body.command}
    else:
        payload = {"source": body.source.model_dump(), "options": body.options.model_dump()}

    task = models.Task(
        type=body.type,
        payload=payload,
        requested_worker_id=body.worker_id,
        created_by=user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    await hub.broadcast(dispatcher.task_event(task))
    await dispatcher.try_dispatch(db)
    db.refresh(task)
    return serialize(task)


@router.get("", dependencies=[Depends(require(Perm.TASK_VIEW))])
def list_tasks(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(models.Task)
    if status:
        q = q.filter(models.Task.status == status)
    total = q.count()
    tasks = q.order_by(models.Task.created_at.desc()).offset(offset).limit(min(limit, 200)).all()
    return {"total": total, "tasks": [serialize(t) for t in tasks]}


@router.get("/{task_id}", dependencies=[Depends(require(Perm.TASK_VIEW))])
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(models.Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return serialize(task, include_output=True)


@router.post("/{task_id}/cancel", dependencies=[Depends(require(Perm.TASK_VIEW))])
async def cancel_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(models.Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status == "pending":
        await dispatcher.finish_task(db, task, "cancelled")
    elif task.status in dispatcher.ACTIVE_STATUSES and task.worker:
        await registry.send(task.worker.client_id, {"type": "cancel", "task_id": task.id})
    else:
        raise HTTPException(status_code=409, detail=f"Cannot cancel task in status {task.status}")
    return serialize(task)
