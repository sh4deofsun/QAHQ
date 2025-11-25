from typing import Dict, List
from fastapi import WebSocket
import json

class WorkerManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.worker_capabilities: Dict[str, List[str]] = {}

    async def connect(self, websocket: WebSocket, client_id: str, capabilities: List[str]):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.worker_capabilities[client_id] = capabilities
        print(f"Worker {client_id} connected with capabilities: {capabilities}")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.worker_capabilities:
            del self.worker_capabilities[client_id]
        print(f"Worker {client_id} disconnected")

    async def send_personal_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(json.dumps(message))
            return True
        return False

    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            await connection.send_text(json.dumps(message))

manager = WorkerManager()
