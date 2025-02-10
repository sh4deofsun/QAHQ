from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Annotated
from robot.api import ExecutionResult

router = APIRouter()

class TestTags:
    def __init__(self):
        self.excluded_tags = []
        self.included_tags = ["TestCount"]

    def get_test_tags(self, suite : dict):
        if "suites" in suite.keys():
            for sub_suite in suite["suites"]:
                self.get_test_tags(sub_suite)
        elif "tests" in suite.keys():
            for test in suite["tests"]:
                print(test["name"])
                print(test["tags"])

    def get_test_count(self, output_xml_path):
        result = ExecutionResult(output_xml_path)
        print(f"Total: {result.statistics.total.total}")
        print(f"Failed: {result.statistics.total.failed}")
        print(f"Passed: {result.statistics.total.passed}")
        print(f"Skipped: {result.statistics.total.skipped}")
        

@router.post("/get_test_count/")
async def get_test_count(file: Annotated[UploadFile | None, File()] = None) -> dict:
    test_tags = TestTags()
    if not file:
        return HTTPException(detail={'message': 'There was no file.'}, status_code=400)
    else:
        file_content = await file.read()
        test_tags.get_test_count(file_content)
        return {"filename": file.filename}
