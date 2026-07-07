# QAHQ — Quality Assurance Headquarters

Centralized master-worker application for QA teams. HQ dispatches RobotFramework
suites and shell commands to remote workers, collects results and artifacts, and
exposes system state to a web UI and to AI agents over MCP.

See [PRD.md](PRD.md) for the full specification.

## Architecture

- **backend/** — FastAPI HQ server (REST + WebSocket + MCP).
- **worker/** — standalone worker client, installed on each runner machine.
- **frontend/** — React + Vite + TypeScript web UI.
- **docker/** — Docker Compose (HQ + PostgreSQL + nginx) for production.

## Local development

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # set SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD
alembic upgrade head          # or rely on create_all at startup for SQLite
uvicorn app.main:app --reload
```

API docs at http://localhost:8000/docs. Runs on SQLite by default.

### Frontend

```bash
cd frontend
npm install
npm run dev                   # http://localhost:5173, proxies /api and /ws to :8000
```

### Worker

```bash
cd worker
pip install -e .              # add [robot] extra for RobotFramework support
QAHQ_URL=ws://localhost:8000 QAHQ_CLIENT_ID=runner-01 QAHQ_TOKEN=<token> qahq-worker
```

Register the worker in the UI (Workers → Register worker) to obtain the token.

## Tests

```bash
cd backend && pytest
```

## Production

```bash
cd docker
export POSTGRES_PASSWORD=... SECRET_KEY=... ADMIN_PASSWORD=...
docker compose up -d --build
```

nginx serves the UI and proxies the API/WS on port `${HTTP_PORT:-8080}`. For real
deployments terminate TLS in nginx (add a 443 server block + certificates) and
point workers at `wss://<host>`.

## MCP

Set `MCP_API_KEY` to enable the read-only MCP server at `/mcp` (streamable HTTP).
Clients authenticate with the `x-api-key` header. Tools: `get_worker_status`,
`list_test_results`, `list_tasks`, `get_task`, `get_recent_logs`.
