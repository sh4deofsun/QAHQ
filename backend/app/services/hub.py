import json
import logging

from fastapi import WebSocket

log = logging.getLogger(__name__)


class UIHub:
    """Fan-out of system events to connected browser sessions.

    ponytail: broadcasts every event to every authenticated UI socket;
    per-permission event filtering if the audience ever needs narrowing.
    """

    def __init__(self):
        self.connections: set[WebSocket] = set()

    def add(self, ws: WebSocket) -> None:
        self.connections.add(ws)

    def remove(self, ws: WebSocket) -> None:
        self.connections.discard(ws)

    async def broadcast(self, event: dict) -> None:
        message = json.dumps(event, default=str)
        for ws in list(self.connections):
            try:
                await ws.send_text(message)
            except Exception:
                self.connections.discard(ws)


hub = UIHub()
