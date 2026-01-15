from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import Annotated
from robot.api import ExecutionResult
from sqlalchemy.orm import Session
from ...Databases import database, models

router = APIRouter()

class TestTags:
    def __init__(self):
        self.excluded_tags = []
        self.included_tags = ["TestCount"]

    def get_test_tags(self, suite : dict):
        if "suites" in suite:
            for sub_suite in suite["suites"]:
                self.get_test_tags(sub_suite)
        elif "tests" in suite:
            for test in suite["tests"]:
                print(test["name"])
                print(test["tags"])

    def get_test_count(self, output_xml_path):
        result = ExecutionResult(output_xml_path)
        return result.statistics.total

@router.post("/get_test_count/")
async def get_test_count(
    file: Annotated[UploadFile | None, File()] = None,
    db: Session = Depends(database.get_db)
) -> dict:
    test_tags = TestTags()
    if not file:
        return HTTPException(detail={'message': 'There was no file.'}, status_code=400)
    else:
        # Save temp file to process
        content = await file.read()
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
            
        stats = test_tags.get_test_count(tmp_path)
        
        # Save to DB
        test_result = models.TestResult(
            suite_name=file.filename, # Or parse from XML
            total_tests=stats.total,
            passed_tests=stats.passed,
            failed_tests=stats.failed,
            skipped_tests=stats.skipped,
            report_path=file.filename # Placeholder
        )
        db.add(test_result)
        db.commit()
        
        return {
            "filename": file.filename,
            "total": stats.total,
            "passed": stats.passed,
            "failed": stats.failed,
            "skipped": stats.skipped
        }
