def test_login_and_me(client, admin_headers):
    r = client.get("/api/auth/me", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == "admin"
    assert "user:manage" in body["permissions"]  # admin role has everything


def test_bad_password_rejected(client):
    r = client.post("/api/auth/token", data={"username": "admin", "password": "wrong"})
    assert r.status_code == 401


def test_no_token_rejected(client):
    assert client.get("/api/workers").status_code == 401


def test_rbac_denies_missing_permission(client, admin_headers):
    client.post(
        "/api/admin/roles",
        json={"name": "viewer", "permissions": ["task:view", "worker:view"]},
        headers=admin_headers,
    )
    client.post(
        "/api/admin/users",
        json={"username": "bob", "password": "bobpass", "roles": ["viewer"]},
        headers=admin_headers,
    )
    token = client.post("/api/auth/token", data={"username": "bob", "password": "bobpass"}).json()[
        "access_token"
    ]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/api/tasks", headers=headers).status_code == 200
    assert client.get("/api/workers", headers=headers).status_code == 200
    # no create/manage permissions
    r = client.post("/api/tasks", json={"type": "run_command", "command": "ls"}, headers=headers)
    assert r.status_code == 403
    assert client.post("/api/workers", json={"client_id": "x"}, headers=headers).status_code == 403
    assert client.get("/api/admin/users", headers=headers).status_code == 403


def test_admin_role_locked(client, admin_headers):
    roles = client.get("/api/admin/roles", headers=admin_headers).json()
    admin_role = next(r for r in roles if r["name"] == "admin")
    r = client.patch(
        f"/api/admin/roles/{admin_role['id']}", json={"permissions": []}, headers=admin_headers
    )
    assert r.status_code == 400
