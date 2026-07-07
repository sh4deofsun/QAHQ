import os
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="qahq-test-"))
os.environ["SECRET_KEY"] = "test-secret"
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["ARTIFACTS_DIR"] = str(_tmp / "artifacts")
os.environ["LOG_DIR"] = str(_tmp / "logs")
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "adminpass"
os.environ["LDAP_SERVER_URL"] = ""  # LDAP off in tests

import pytest
from fastapi.testclient import TestClient

from app.db import models
from app.db.seed import seed
from app.db.session import SessionLocal, engine
from app.main import app
from app.services.hub import hub
from app.services.registry import registry


@pytest.fixture(scope="session")
def _client():
    # One lifespan for the whole session — the MCP session manager cannot be restarted
    with TestClient(app) as c:
        yield c


@pytest.fixture
def client(_client):
    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed(db)
    registry.connections.clear()
    hub.connections.clear()
    yield _client


@pytest.fixture
def admin_token(client):
    r = client.post("/api/auth/token", data={"username": "admin", "password": "adminpass"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def worker_token(client, admin_headers):
    """Register a worker; returns (client_id, token)."""
    r = client.post("/api/workers", json={"client_id": "w1"}, headers=admin_headers)
    assert r.status_code == 201, r.text
    return "w1", r.json()["token"]


def register_worker_ws(ws, client_id, token, capabilities=None):
    import json

    ws.send_text(
        json.dumps(
            {
                "client_id": client_id,
                "token": token,
                "hostname": "testhost",
                "os": "testos",
                "capabilities": capabilities or ["run_command", "robot_execution"],
            }
        )
    )
    return ws.receive_json()
