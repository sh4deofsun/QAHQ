# Product Requirements Document (PRD) — QAHQ

**Version:** 2.0
**Status:** Approved for implementation (full rewrite)
**Context:** Internal production tool for QA teams.

## 1. Introduction

**QAHQ** (Quality Assurance Headquarters) is a centralized master-worker application for QA teams. The HQ server manages a fleet of remote workers that execute RobotFramework test suites and shell commands, collects results and artifacts, and exposes system state to users (web UI) and AI agents (MCP).

## 2. Problem Statement

QA teams struggle with:
- Decentralized test execution and result management across many machines.
- No immediate visibility into test statistics and worker health.
- Manual processing of RobotFramework XML outputs.
- No structured, auditable way to run tests remotely.

## 3. Goals

- **Centralization**: Single entry point for QA operations.
- **Distributed execution**: HQ dispatches work to remote workers over persistent WebSockets.
- **Real-time visibility**: Live worker status, task progress, and streamed command output in the UI.
- **Automation**: Automatic parsing, storage, and reporting of RobotFramework results.
- **AI integration**: Real MCP server so AI agents can query system state.
- **Security**: Production-grade auth (LDAP + local), RBAC, authenticated workers, TLS.

## 4. Architecture Overview

```
┌─────────────┐   WebSocket (token auth)   ┌──────────┐
│   Worker 1  │◄──────────────────────────►│          │
├─────────────┤                            │          │      ┌────────────┐
│   Worker N  │◄──────────────────────────►│  HQ      │◄────►│ PostgreSQL │
└─────────────┘                            │ (FastAPI)│      └────────────┘
                                           │          │
┌─────────────┐   WebSocket (JWT) + REST   │          │      ┌────────────┐
│  Browser UI │◄──────────────────────────►│          │◄────►│ data/      │
└─────────────┘                            │          │      │ artifacts  │
                                           │  /mcp    │      └────────────┘
┌─────────────┐   Streamable HTTP (API key)│          │
│  AI Agents  │◄──────────────────────────►│          │
└─────────────┘                            └──────────┘
```

- Single HQ instance behind nginx (TLS termination, static frontend).
- Workers are outbound-only: they connect to HQ, no inbound ports required on worker machines.

## 5. Functional Requirements

### 5.1 Core System
- **Framework**: FastAPI, Python 3.11+.
- **Protocols**:
    - REST API for CRUD and external integrations.
    - WebSocket `/ws/worker` for HQ↔worker (persistent, token-authenticated).
    - WebSocket `/ws/ui` for HQ↔browser (JWT-authenticated) — pushes worker status changes, task updates, live command output.
- **Middleware**: `X-Process-Time` and `Signature` response headers.
- **Configuration**: All settings via environment variables (pydantic-settings). No hardcoded secrets, no insecure defaults.

### 5.2 Worker System

#### 5.2.1 Registration & Identity
- Admin registers a worker in the UI; HQ generates a unique token (shown once, stored hashed).
- Worker connects with `client_id` + token; HQ verifies against DB. Tokens are revocable per worker.
- On connect, worker reports: hostname, IP, OS, capabilities (e.g. `run_command`, `robot_execution`, `file_transfer`).

#### 5.2.2 Health
- Heartbeat: worker pings every 30 s; no message for 90 s ⇒ HQ marks worker `offline`.
- Worker status (`online` / `busy` / `offline`) persisted in DB and pushed to UI in real time.

#### 5.2.3 Capabilities
- **Command execution**: run shell command, stream stdout/stderr back incrementally, report exit code.
- **Robot execution**: run a RobotFramework suite, upload `output.xml` + `log.html` + `report.html` to HQ on completion.
- **File transfer**: receive files from HQ, send files to HQ (chunked over WebSocket).
- **Git**: clone/pull a test repository at a given branch/ref before execution.

#### 5.2.4 Worker Client
- Standalone Python package (`worker/`), installable via pip on any machine.
- Configured via env vars / config file: HQ URL, client_id, token, workspace directory.
- Auto-reconnect with backoff on connection loss.

### 5.3 Task System
- **Persistence**: every task stored in DB with full lifecycle: `pending → assigned → running → completed | failed | cancelled`.
- **Types**:
    - `robot_run`: test source (git URL + branch + path, **or** path already on worker) + robot options (include/exclude tags, variables). Worker runs suite, uploads artifacts; HQ parses `output.xml` and stores statistics.
    - `run_command`: free-form shell command (permission-gated). Output streamed live to the initiating UI session and stored with the task.
- **Dispatch (hybrid)**:
    - Manual: user selects a specific worker.
    - Automatic: HQ picks an online, non-busy worker having the required capability; if none free, task queues as `pending`.
- **Results**: task record links to stored artifacts and parsed statistics; UI shows history with filters.

### 5.4 Test Results & Artifacts
- HQ parses uploaded `output.xml` via `robot.api.ExecutionResult`: total / passed / failed / skipped, suite name, execution time.
- Artifacts stored on local disk under `data/artifacts/{task_id}/`; paths recorded in DB.
- UI serves `log.html` / `report.html` for viewing and download.
- Standalone XML upload endpoint retained for CI integrations: `POST /api/test-results/upload` (parses, stores stats + artifact).

### 5.5 Authentication & Authorization

#### 5.5.1 Authentication
- **LDAP/LDAPS**: primary method for team members (search-then-bind; configurable server, base DN, user filter). First successful login auto-provisions a local shadow user.
- **Local**: for admin/service accounts; passwords hashed (pbkdf2_sha256 or argon2).
- **Session**: JWT access tokens; secret from env (startup fails if unset).

#### 5.5.2 RBAC (dynamic)
- Tables: `roles`, `permissions`, `role_permissions`, `user_roles`.
- Permissions are a fixed enum in code, e.g.:
    - `worker:view`, `worker:manage` (register/revoke tokens)
    - `task:view`, `task:create_robot`, `task:create_command`
    - `result:view`
    - `user:manage`, `role:manage`
- Roles created and assigned via Admin UI. Seed data: `admin` role (all permissions) + initial admin user created by CLI/first-run script.
- Every REST endpoint and WebSocket action guarded by permission checks.

### 5.6 MCP (AI Integration)
- Real Model Context Protocol server via the official Python SDK (FastMCP), mounted on the FastAPI app at `/mcp` (streamable HTTP).
- **Read-only** in v1. Protected by API key (env-configured).
- Tools:
    - `get_worker_status` — workers, status, capabilities, current task.
    - `list_test_results` — recent results with statistics, filterable.
    - `get_task` / `list_tasks` — task details and history.
    - `get_recent_logs` — recent execution logs for debugging.

### 5.7 Frontend
- **Stack**: React + Vite + TypeScript. Vanilla CSS, dark theme (CSS variables). No UI framework.
- **Real-time**: single WebSocket connection to `/ws/ui`; REST for initial loads and mutations.
- **Pages**:
    - **Login** — LDAP or local credentials.
    - **Dashboard** — summary cards (workers online, tasks running, last results), live worker list.
    - **Workers** — worker detail, register worker (token shown once), revoke token, run command with live streamed output (permission-gated).
    - **Tasks** — create robot run (git source or worker path, robot options, manual/auto dispatch), task history with status, artifact viewing/download.
    - **Admin** — user management, role & permission management (RBAC), visible only with `user:manage` / `role:manage`.
- UI elements hidden/disabled per user permissions.

### 5.8 Operations
- **Logging**: structured logging to stdout + rotating file; request logging middleware.
- **Email notifications**: out of scope for v1 (future scope, see §8).

## 6. Technical Requirements

| Area | Choice |
|---|---|
| Language | Python 3.11+ |
| Web framework | FastAPI + uvicorn |
| ORM / migrations | SQLAlchemy 2.x + Alembic |
| Database | PostgreSQL (production), SQLite (development) — engine via `DATABASE_URL` |
| Robot integration | `robotframework` (`ExecutionResult` for parsing) |
| Auth | `python-jose` (JWT), `passlib`, `ldap3` |
| MCP | official `mcp` Python SDK (FastMCP) |
| Worker client | standalone package: `websockets`, stdlib |
| Frontend | React 18+, Vite, TypeScript |
| Deployment | Docker Compose: HQ + PostgreSQL + nginx (TLS termination, static frontend) |
| Testing | pytest — critical paths: auth, RBAC, task lifecycle, worker protocol |

### 6.1 Repository Layout
```
backend/
  app/
    api/            # routers (auth, workers, tasks, results, admin, ws)
    core/           # config, security, permissions enum
    db/             # models, session, migrations (alembic)
    services/       # task dispatch, result parsing, worker registry
    mcp/            # MCP server mount
  tests/
worker/             # standalone worker client package
frontend/           # React + Vite + TS
docker/             # compose, nginx config, Dockerfiles
data/               # runtime artifacts (gitignored)
```

## 7. Non-Functional Requirements
- **Security**: TLS via nginx; no secret defaults in code; worker tokens hashed; free-form command execution restricted by RBAC permission.
- **Reliability**: workers auto-reconnect; queued tasks survive HQ restart (DB-persisted); heartbeat-based failure detection.
- **Performance**: low-latency API; command output streamed, not buffered.
- **Portability**: single-command local dev (SQLite, no Docker required); single compose file for production.

## 8. Future Scope
- Email notifications for failed test runs.
- MCP write tools (task triggering) gated by RBAC.
- LDAP group → role auto-mapping.
- Object storage (S3/MinIO) for artifacts.
- CI/CD webhook integrations.

## 9. Assumptions & Constraints
- Single HQ instance (no horizontal scaling in v1).
- Workers have outbound network access to HQ; no inbound ports needed on workers.
- Test repositories are reachable from worker machines (git credentials managed on the worker).
- Local disk is sufficient for artifact storage in v1.
