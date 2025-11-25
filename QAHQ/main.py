"""
QAHQ Main Application
"""
import time
from typing import Annotated, List

from fastapi import FastAPI, Request, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Body
from fastapi.responses import JSONResponse, FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .Databases import models, database
from .Securities import auth
from .Applications.TestCounterSingleton import test_counter
from .Applications.WorkerManager.manager import manager
from .Applications.MCP import server as mcp_server

from fastapi.middleware.cors import CORSMiddleware

# Initialize Database
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title="QAHQ",
    description="QAHQ - Quality Assurance Headquarters",
    version="1.0.0",
    contact={
        "name": "BY",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include existing routers
app.include_router(router=test_counter.router, tags=["Robot Framework"])
app.include_router(router=mcp_server.router, tags=["MCP"])

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["Signature"] = "SQAA-T64572-BY"
    return response

@app.get("/")
def read_root():
    return {"Hello": "QAHQ World"}

# Authentication Endpoints
@app.post("/token", response_model=dict)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(database.get_db)
):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(
        data={"sub": user.username}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me")
async def read_users_me(current_user: Annotated[models.User, Depends(auth.get_current_user)]):
    return {"username": current_user.username, "is_admin": current_user.is_admin}

# WebSocket Endpoint for Workers
@app.websocket("/ws/worker/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    # In a real scenario, we might want to authenticate the worker here too (e.g. via header token)
    # For now, we assume capabilities are sent as the first message or query param. 
    # Let's assume query param for simplicity or wait for first message.
    # We'll wait for the first message to be the registration/capabilities.
    
    await websocket.accept() # Accept first to receive data
    try:
        data = await websocket.receive_text()
        # Expecting JSON: {"capabilities": ["run_command", ...]}
        import json
        msg = json.loads(data)
        capabilities = msg.get("capabilities", [])
        
        # Re-register with manager properly
        # Note: manager.connect accepts the websocket, but we already accepted it. 
        # We should adjust manager.connect or just register it.
        # Let's adjust usage:
        manager.active_connections[client_id] = websocket
        manager.worker_capabilities[client_id] = capabilities
        print(f"Worker {client_id} connected with capabilities: {capabilities}")
        
        await websocket.send_text(json.dumps({"status": "registered"}))
        
        while True:
            data = await websocket.receive_text()
            # Handle worker messages (e.g. task results, heartbeat)
            print(f"Received from {client_id}: {data}")
            # Process message...
            
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        print(f"Error with worker {client_id}: {e}")
        manager.disconnect(client_id)

# Example endpoint to trigger a command on a worker
@app.post("/worker/{client_id}/run_command")
async def run_command_on_worker(
    client_id: str, 
    command: str = Body(..., embed=True),
    current_user: models.User = Depends(auth.get_current_user)
):
    if not current_user.is_admin: # Only admins can run commands
         raise HTTPException(status_code=403, detail="Not authorized")
         
    message = {"type": "run_command", "command": command}
    success = await manager.send_personal_message(message, client_id)
    if not success:
        raise HTTPException(status_code=404, detail="Worker not found")
    return {"status": "command_sent"}

favicon_path = "favicon.ico"
@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse(favicon_path)
