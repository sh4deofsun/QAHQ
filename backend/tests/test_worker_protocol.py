import json

import pytest
from starlette.websockets import WebSocketDisconnect

from .conftest import register_worker_ws


def test_worker_register_ok(client, worker_token, admin_headers):
    client_id, token = worker_token
    with client.websocket_connect("/ws/worker") as ws:
        resp = register_worker_ws(ws, client_id, token)
        assert resp == {"type": "registered"}
        workers = client.get("/api/workers", headers=admin_headers).json()
        assert workers[0]["status"] == "online"
        assert workers[0]["hostname"] == "testhost"
    # after disconnect
    workers = client.get("/api/workers", headers=admin_headers).json()
    assert workers[0]["status"] == "offline"


def test_worker_bad_token_rejected(client, worker_token):
    client_id, _ = worker_token
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/worker") as ws:
            ws.send_text(json.dumps({"client_id": client_id, "token": "wrong"}))
            ws.receive_text()


def test_unregistered_client_rejected(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/worker") as ws:
            ws.send_text(json.dumps({"client_id": "ghost", "token": "x"}))
            ws.receive_text()


def test_ui_socket_requires_valid_jwt(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/ui?token=garbage"):
            pass


def test_ui_socket_receives_worker_events(client, worker_token, admin_token):
    client_id, token = worker_token
    with client.websocket_connect(f"/ws/ui?token={admin_token}") as ui:
        with client.websocket_connect("/ws/worker") as ws:
            register_worker_ws(ws, client_id, token)
            event = ui.receive_json()
            assert event["event"] == "worker_status"
            assert event["worker"]["client_id"] == client_id
            assert event["worker"]["status"] == "online"
