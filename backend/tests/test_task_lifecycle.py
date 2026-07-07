import base64
import json

from .conftest import register_worker_ws

ROBOT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<robot generator="Robot 7.1.1" generated="2026-07-07T10:00:00.000000" rpa="false" schemaversion="5">
<suite id="s1" name="Demo">
<test id="s1-t1" name="Passing Test" line="3">
<status status="PASS" start="2026-07-07T10:00:00.100000" elapsed="0.01"/>
</test>
<test id="s1-t2" name="Failing Test" line="7">
<status status="FAIL" start="2026-07-07T10:00:00.200000" elapsed="0.01">boom</status>
</test>
<status status="FAIL" start="2026-07-07T10:00:00.000000" elapsed="0.5"/>
</suite>
<statistics>
<total><stat pass="1" fail="1" skip="0">All Tests</stat></total>
<tag/>
<suite><stat pass="1" fail="1" skip="0" id="s1" name="Demo">Demo</stat></suite>
</statistics>
<errors/>
</robot>
"""


def test_command_task_full_lifecycle(client, worker_token, admin_headers):
    client_id, token = worker_token
    with client.websocket_connect("/ws/worker") as ws:
        register_worker_ws(ws, client_id, token)

        r = client.post(
            "/api/tasks", json={"type": "run_command", "command": "echo hi"}, headers=admin_headers
        )
        assert r.status_code == 201
        task_id = r.json()["id"]

        msg = ws.receive_json()
        assert msg["type"] == "task"
        assert msg["task_id"] == task_id
        assert msg["payload"]["command"] == "echo hi"

        ws.send_text(json.dumps({"type": "task_status", "task_id": task_id, "status": "running"}))
        ws.send_text(json.dumps({"type": "output", "task_id": task_id, "data": "hi\n"}))
        ws.send_text(
            json.dumps(
                {"type": "task_result", "task_id": task_id, "status": "completed", "returncode": 0}
            )
        )

        # worker socket stays open; poll REST until finalized
        for _ in range(50):
            task = client.get(f"/api/tasks/{task_id}", headers=admin_headers).json()
            if task["status"] == "completed":
                break
        assert task["status"] == "completed"
        assert task["returncode"] == 0
        assert task["output"] == "hi\n"


def test_task_queues_when_no_worker(client, admin_headers):
    r = client.post(
        "/api/tasks", json={"type": "run_command", "command": "ls"}, headers=admin_headers
    )
    assert r.status_code == 201
    assert r.json()["status"] == "pending"

    r = client.post(f"/api/tasks/{r.json()['id']}/cancel", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


def test_robot_task_uploads_artifacts_and_parses_result(client, worker_token, admin_headers):
    client_id, token = worker_token
    with client.websocket_connect("/ws/worker") as ws:
        register_worker_ws(ws, client_id, token)

        r = client.post(
            "/api/tasks",
            json={"type": "robot_run", "source": {"path": "/suites/demo"}, "worker_id": 1},
            headers=admin_headers,
        )
        assert r.status_code == 201, r.text
        task_id = r.json()["id"]
        msg = ws.receive_json()
        assert msg["task_type"] == "robot_run"

        ws.send_text(json.dumps({"type": "task_status", "task_id": task_id, "status": "running"}))
        # upload output.xml in two chunks, then finish
        ws.send_text(json.dumps({"type": "file_begin", "task_id": task_id, "filename": "output.xml"}))
        data = ROBOT_XML.encode()
        half = len(data) // 2
        for chunk in (data[:half], data[half:]):
            ws.send_text(
                json.dumps({"type": "file_chunk", "data": base64.b64encode(chunk).decode()})
            )
        ws.send_text(json.dumps({"type": "file_end"}))
        ws.send_text(
            json.dumps(
                {"type": "task_result", "task_id": task_id, "status": "completed", "returncode": 1}
            )
        )

        for _ in range(50):
            task = client.get(f"/api/tasks/{task_id}", headers=admin_headers).json()
            if task["status"] == "completed":
                break
        assert task["status"] == "completed"

    results = client.get("/api/results", headers=admin_headers).json()["results"]
    assert len(results) == 1
    assert results[0] == {
        **results[0],
        "suite_name": "Demo",
        "total": 2,
        "passed": 1,
        "failed": 1,
        "skipped": 0,
        "task_id": task_id,
    }
    # artifact served back
    files = client.get(
        f"/api/results/{results[0]['id']}/artifacts", headers=admin_headers
    ).json()["artifacts"]
    assert files == ["output.xml"]


def test_worker_disconnect_fails_running_task(client, worker_token, admin_headers):
    client_id, token = worker_token
    with client.websocket_connect("/ws/worker") as ws:
        register_worker_ws(ws, client_id, token)
        r = client.post(
            "/api/tasks", json={"type": "run_command", "command": "sleep 100"}, headers=admin_headers
        )
        task_id = r.json()["id"]
        ws.receive_json()  # task delivered
        # socket closes here without a result

    for _ in range(50):
        task = client.get(f"/api/tasks/{task_id}", headers=admin_headers).json()
        if task["status"] == "failed":
            break
    assert task["status"] == "failed"
    assert "disconnected" in task["error"]
