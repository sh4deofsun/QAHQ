from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from typing import Annotated
from robot.api import ExecutionResult
from robot import rebot

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
        
    

@router.post("/send_test_report/")
async def send_test_report(file: Annotated[UploadFile | None, File()] = None) -> dict:
    test_tags = TestTags()
    if not file:
        return HTTPException(detail={'message': 'There was no file.'}, status_code=400)
    else:
        file_content = await file.read()
        test_tags.get_test_count(file_content)
        file1, file2 = rebot(file_content, outputdir="__Example__/rebot_example/Result", output="output.xml")
        return {"filename": file.filename, "file1": file1.filename, "file2": file2.filename}
