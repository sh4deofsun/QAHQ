"""QAHQ worker client.

Config via environment:
  QAHQ_URL        e.g. wss://hq.example.com  (required)
  QAHQ_TOKEN      worker token issued by HQ  (required)
  QAHQ_CLIENT_ID  defaults to hostname
  QAHQ_WORKSPACE  defaults to ~/.qahq-worker
"""

import asyncio
import base64
import hashlib
import importlib.util
import json
import logging
import os
import platform
import shutil
import signal
import socket
import sys
from pathlib import Path

import websockets

log = logging.getLogger("qahq-worker")

HEARTBEAT_SECONDS = 30
CHUNK_SIZE = 48 * 1024
ARTIFACT_FILES = ("output.xml", "log.html", "report.html")


def detect_capabilities() -> list[str]:
    caps = ["run_command", "file_transfer"]
    if importlib.util.find_spec("robot"):
        caps.append("robot_execution")
    if shutil.which("git"):
        caps.append("git")
    return caps


class Worker:
    def __init__(self):
        self.url = os.environ["QAHQ_URL"].rstrip("/") + "/ws/worker"
        self.token = os.environ["QAHQ_TOKEN"]
        self.client_id = os.environ.get("QAHQ_CLIENT_ID", socket.gethostname())
        self.workspace = Path(os.environ.get("QAHQ_WORKSPACE", Path.home() / ".qahq-worker"))
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.current_process: asyncio.subprocess.Process | None = None

    # ---- messaging helpers ----

    async def send(self, ws, message: dict) -> None:
        await ws.send(json.dumps(message))

    async def stream_output(self, ws, task_id: int, stream: asyncio.StreamReader) -> None:
        while True:
            line = await stream.readline()
            if not line:
                break
            await self.send(ws, {"type": "output", "task_id": task_id, "data": line.decode(errors="replace")})

    async def upload_file(self, ws, task_id: int, path: Path) -> None:
        await self.send(ws, {"type": "file_begin", "task_id": task_id, "filename": path.name})
        with open(path, "rb") as f:
            while chunk := f.read(CHUNK_SIZE):
                await self.send(ws, {"type": "file_chunk", "data": base64.b64encode(chunk).decode()})
        await self.send(ws, {"type": "file_end"})

    # ---- task execution ----

    async def run_process(self, ws, task_id: int, args_or_cmd, shell: bool, cwd: Path | None = None) -> int:
        if shell:
            proc = await asyncio.create_subprocess_shell(
                args_or_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=cwd,
            )
        else:
            proc = await asyncio.create_subprocess_exec(
                *args_or_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=cwd,
            )
        self.current_process = proc
        try:
            await self.stream_output(ws, task_id, proc.stdout)
            return await proc.wait()
        finally:
            self.current_process = None

    async def handle_run_command(self, ws, task_id: int, payload: dict) -> None:
        rc = await self.run_process(ws, task_id, payload["command"], shell=True)
        await self.send(
            ws,
            {
                "type": "task_result",
                "task_id": task_id,
                "status": "completed" if rc == 0 else "failed",
                "returncode": rc,
                "error": "" if rc == 0 else f"exit code {rc}",
            },
        )

    async def prepare_source(self, ws, task_id: int, source: dict) -> Path:
        """Returns the suite path to run. Clones/updates the git repo when given."""
        git_url = source.get("git_url", "")
        if not git_url:
            return Path(source["path"])

        repo_dir = self.workspace / "repos" / hashlib.sha1(git_url.encode()).hexdigest()[:12]
        ref = source.get("git_ref") or "HEAD"
        if not repo_dir.exists():
            rc = await self.run_process(ws, task_id, ["git", "clone", git_url, str(repo_dir)], shell=False)
        else:
            rc = await self.run_process(ws, task_id, ["git", "-C", str(repo_dir), "fetch", "--all"], shell=False)
        if rc != 0:
            raise RuntimeError("git clone/fetch failed")
        rc = await self.run_process(ws, task_id, ["git", "-C", str(repo_dir), "checkout", ref], shell=False)
        if rc == 0 and source.get("git_ref"):
            # move branch to remote tip if it's a branch; harmless failure for tags/SHAs
            await self.run_process(ws, task_id, ["git", "-C", str(repo_dir), "pull", "--ff-only"], shell=False)
        if rc != 0:
            raise RuntimeError(f"git checkout {ref} failed")
        return repo_dir / source.get("path", ".")

    async def handle_robot_run(self, ws, task_id: int, payload: dict) -> None:
        try:
            suite_path = await self.prepare_source(ws, task_id, payload.get("source", {}))
        except RuntimeError as e:
            await self.send(
                ws, {"type": "task_result", "task_id": task_id, "status": "failed", "error": str(e)}
            )
            return

        out_dir = self.workspace / "runs" / str(task_id)
        out_dir.mkdir(parents=True, exist_ok=True)
        options = payload.get("options", {})
        cmd = [sys.executable, "-m", "robot", "--outputdir", str(out_dir)]
        for tag in options.get("include_tags", []):
            cmd += ["--include", tag]
        for tag in options.get("exclude_tags", []):
            cmd += ["--exclude", tag]
        for key, value in options.get("variables", {}).items():
            cmd += ["--variable", f"{key}:{value}"]
        cmd.append(str(suite_path))

        rc = await self.run_process(ws, task_id, cmd, shell=False)

        uploaded = False
        for name in ARTIFACT_FILES:
            artifact = out_dir / name
            if artifact.exists():
                await self.upload_file(ws, task_id, artifact)
                uploaded = True

        # robot exit code = number of failed tests; the run itself succeeded if output exists
        status = "completed" if uploaded else "failed"
        await self.send(
            ws,
            {
                "type": "task_result",
                "task_id": task_id,
                "status": status,
                "returncode": rc,
                "error": "" if uploaded else "robot produced no output.xml",
            },
        )

    async def handle_task(self, ws, msg: dict) -> None:
        task_id = msg["task_id"]
        await self.send(ws, {"type": "task_status", "task_id": task_id, "status": "running"})
        try:
            if msg["task_type"] == "run_command":
                await self.handle_run_command(ws, task_id, msg["payload"])
            elif msg["task_type"] == "robot_run":
                await self.handle_robot_run(ws, task_id, msg["payload"])
            else:
                await self.send(
                    ws,
                    {
                        "type": "task_result",
                        "task_id": task_id,
                        "status": "failed",
                        "error": f"Unknown task type {msg['task_type']}",
                    },
                )
        except asyncio.CancelledError:
            await self.send(
                ws, {"type": "task_result", "task_id": task_id, "status": "cancelled", "error": "Cancelled"}
            )
        except Exception as e:
            log.exception("Task %s crashed", task_id)
            await self.send(
                ws, {"type": "task_result", "task_id": task_id, "status": "failed", "error": str(e)}
            )

    # ---- main loop ----

    async def heartbeat(self, ws) -> None:
        while True:
            await asyncio.sleep(HEARTBEAT_SECONDS)
            await self.send(ws, {"type": "heartbeat"})

    async def session(self) -> None:
        log.info("Connecting to %s as %s", self.url, self.client_id)
        async with websockets.connect(self.url, max_size=16 * 1024 * 1024) as ws:
            await self.send(
                ws,
                {
                    "client_id": self.client_id,
                    "token": self.token,
                    "hostname": socket.gethostname(),
                    "os": f"{platform.system()} {platform.release()}",
                    "capabilities": detect_capabilities(),
                },
            )
            reply = json.loads(await ws.recv())
            if reply.get("type") != "registered":
                raise RuntimeError(f"Registration rejected: {reply}")
            log.info("Registered. Capabilities: %s", detect_capabilities())

            heartbeat = asyncio.create_task(self.heartbeat(ws))
            current_task: asyncio.Task | None = None
            try:
                async for raw in ws:
                    msg = json.loads(raw)
                    if msg.get("type") == "task":
                        current_task = asyncio.create_task(self.handle_task(ws, msg))
                    elif msg.get("type") == "cancel":
                        if self.current_process:
                            self.current_process.send_signal(signal.SIGTERM)
                        if current_task:
                            current_task.cancel()
                    elif msg.get("type") == "file":
                        incoming = self.workspace / "incoming"
                        incoming.mkdir(exist_ok=True)
                        target = incoming / Path(msg["filename"]).name
                        target.write_bytes(base64.b64decode(msg["data"]))
                        log.info("Received file %s", target)
            finally:
                heartbeat.cancel()
                if current_task:
                    current_task.cancel()

    async def run_forever(self) -> None:
        backoff = 1
        while True:
            try:
                await self.session()
                backoff = 1
            except Exception as e:
                log.warning("Connection lost (%s), retrying in %ss", e, backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    missing = [v for v in ("QAHQ_URL", "QAHQ_TOKEN") if not os.environ.get(v)]
    if missing:
        sys.exit(f"Missing required environment variables: {', '.join(missing)}")
    try:
        asyncio.run(Worker().run_forever())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
