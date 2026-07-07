import json
import logging

from fastapi import WebSocket

log = logging.getLogger(__name__)


class WorkerRegistry:
    """Live worker connections. DB rows are the durable record; this is the wire."""

    def __init__(self):
        self.connections: dict[str, WebSocket] = {}

    def add(self, client_id: str, ws: WebSocket) -> None:
        self.connections[client_id] = ws

    def remove(self, client_id: str) -> None:
        self.connections.pop(client_id, None)

    def is_online(self, client_id: str) -> bool:
        return client_id in self.connections

    async def send(self, client_id: str, message: dict) -> bool:
        ws = self.connections.get(client_id)
        if not ws:
            return False
        try:
            await ws.send_text(json.dumps(message, default=str))
            return True
        except Exception as e:
            log.warning("Send to worker %s failed: %s", client_id, e)
            return False


registry = WorkerRegistry()
