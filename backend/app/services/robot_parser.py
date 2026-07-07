import logging
from pathlib import Path

from sqlalchemy.orm import Session

from ..db import models

log = logging.getLogger(__name__)


def parse_output_xml(db: Session, xml_path: Path, task_id: int | None, artifact_dir: str) -> models.TestResult | None:
    """Parse a RobotFramework output.xml and persist a TestResult row."""
    try:
        from robot.api import ExecutionResult

        result = ExecutionResult(str(xml_path))
        stats = result.statistics.total
        row = models.TestResult(
            task_id=task_id,
            suite_name=result.suite.name or xml_path.name,
            total=stats.total,
            passed=stats.passed,
            failed=stats.failed,
            skipped=stats.skipped,
            elapsed_ms=result.suite.elapsedtime or 0,
            artifact_dir=artifact_dir,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    except Exception as e:
        log.error("Failed to parse %s: %s", xml_path, e)
        return None
