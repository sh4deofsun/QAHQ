import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.permissions import Perm
from ..db import models
from ..db.session import get_db
from ..services.robot_parser import parse_output_xml
from .deps import require

router = APIRouter(prefix="/api/results", tags=["results"])


def serialize(r: models.TestResult) -> dict:
    return {
        "id": r.id,
        "task_id": r.task_id,
        "suite_name": r.suite_name,
        "total": r.total,
        "passed": r.passed,
        "failed": r.failed,
        "skipped": r.skipped,
        "elapsed_ms": r.elapsed_ms,
        "has_artifacts": bool(r.artifact_dir),
        "created_at": r.created_at,
    }


@router.get("", dependencies=[Depends(require(Perm.RESULT_VIEW))])
def list_results(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    q = db.query(models.TestResult)
    total = q.count()
    rows = q.order_by(models.TestResult.created_at.desc()).offset(offset).limit(min(limit, 200)).all()
    return {"total": total, "results": [serialize(r) for r in rows]}


@router.post("/upload", dependencies=[Depends(require(Perm.RESULT_UPLOAD))], status_code=201)
async def upload_output_xml(file: UploadFile, db: Session = Depends(get_db)):
    """Standalone output.xml upload for CI integrations."""
    content = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".xml") as tmp:
        tmp.write(content)
        tmp.flush()
        result = parse_output_xml(db, Path(tmp.name), task_id=None, artifact_dir="")
    if not result:
        raise HTTPException(status_code=400, detail="Not a valid RobotFramework output.xml")
    # Keep the uploaded XML as an artifact
    artifact_dir = settings.artifacts_dir / f"upload-{result.id}"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "output.xml").write_bytes(content)
    result.artifact_dir = str(artifact_dir)
    result.suite_name = result.suite_name or file.filename
    db.commit()
    return serialize(result)


@router.get("/{result_id}/artifacts/{filename}", dependencies=[Depends(require(Perm.RESULT_VIEW))])
def get_artifact(result_id: int, filename: str, db: Session = Depends(get_db)):
    result = db.get(models.TestResult, result_id)
    if not result or not result.artifact_dir:
        raise HTTPException(status_code=404, detail="Result or artifacts not found")
    base = Path(result.artifact_dir).resolve()
    target = (base / filename).resolve()
    if base not in target.parents and target != base:  # path traversal guard
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(target)


@router.get("/{result_id}/artifacts", dependencies=[Depends(require(Perm.RESULT_VIEW))])
def list_artifacts(result_id: int, db: Session = Depends(get_db)):
    result = db.get(models.TestResult, result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    base = Path(result.artifact_dir) if result.artifact_dir else None
    if not base or not base.is_dir():
        return {"artifacts": []}
    return {"artifacts": sorted(f.name for f in base.iterdir() if f.is_file())}
