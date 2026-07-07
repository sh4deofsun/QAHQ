"""Read-only MCP server exposing QAHQ state to AI agents (PRD §5.6)."""

from mcp.server.fastmcp import FastMCP

from ..core.config import settings
from ..db import models
from ..db.session import SessionLocal
from ..services.dispatcher import worker_state

mcp = FastMCP("QAHQ", stateless_http=True, streamable_http_path="/")


@mcp.tool()
def get_worker_status() -> list[dict]:
    """Get all registered workers with their live status, capabilities and current task."""
    with SessionLocal() as db:
        out = []
        for w in db.query(models.Worker).all():
            current = (
                db.query(models.Task)
                .filter(models.Task.worker_id == w.id, models.Task.status.in_(("assigned", "running")))
                .first()
            )
            out.append(
                {
                    "client_id": w.client_id,
                    "hostname": w.hostname,
                    "status": worker_state(db, w),
                    "capabilities": w.capabilities or [],
                    "current_task_id": current.id if current else None,
                    "last_heartbeat": str(w.last_heartbeat),
                }
            )
        return out


@mcp.tool()
def list_test_results(limit: int = 20) -> list[dict]:
    """List recent RobotFramework test results with pass/fail statistics."""
    with SessionLocal() as db:
        rows = (
            db.query(models.TestResult)
            .order_by(models.TestResult.created_at.desc())
            .limit(min(limit, 100))
            .all()
        )
        return [
            {
                "id": r.id,
                "task_id": r.task_id,
                "suite_name": r.suite_name,
                "total": r.total,
                "passed": r.passed,
                "failed": r.failed,
                "skipped": r.skipped,
                "elapsed_ms": r.elapsed_ms,
                "created_at": str(r.created_at),
            }
            for r in rows
        ]


@mcp.tool()
def list_tasks(status: str = "", limit: int = 20) -> list[dict]:
    """List recent tasks, optionally filtered by status (pending/assigned/running/completed/failed/cancelled)."""
    with SessionLocal() as db:
        q = db.query(models.Task)
        if status:
            q = q.filter(models.Task.status == status)
        rows = q.order_by(models.Task.created_at.desc()).limit(min(limit, 100)).all()
        return [
            {
                "id": t.id,
                "type": t.type,
                "status": t.status,
                "worker_id": t.worker_id,
                "error": t.error,
                "created_at": str(t.created_at),
            }
            for t in rows
        ]


@mcp.tool()
def get_task(task_id: int) -> dict:
    """Get full details of a task including its captured output."""
    with SessionLocal() as db:
        t = db.get(models.Task, task_id)
        if not t:
            return {"error": f"Task {task_id} not found"}
        return {
            "id": t.id,
            "type": t.type,
            "status": t.status,
            "payload": t.payload,
            "worker_id": t.worker_id,
            "output": t.output[-20000:],
            "returncode": t.returncode,
            "error": t.error,
            "created_at": str(t.created_at),
            "finished_at": str(t.finished_at),
        }


@mcp.tool()
def get_recent_logs(lines: int = 100) -> str:
    """Read the tail of the HQ application log for debugging."""
    log_file = settings.log_dir / "qahq.log"
    if not log_file.exists():
        return "(no log file yet)"
    content = log_file.read_text(errors="replace").splitlines()
    return "\n".join(content[-min(lines, 1000):])
