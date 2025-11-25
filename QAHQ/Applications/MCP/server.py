from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ...Databases import database, models
from ...Applications.WorkerManager.manager import manager

router = APIRouter()

@router.get("/mcp/tools")
async def list_tools():
    """
    List available tools for the AI agent.
    """
    return [
        {
            "name": "get_worker_status",
            "description": "Get the status of all connected workers",
            "parameters": {}
        },
        {
            "name": "list_test_results",
            "description": "List recent test results",
            "parameters": {
                "limit": "integer (optional)"
            }
        }
    ]

@router.post("/mcp/tools/get_worker_status")
async def get_worker_status():
    """
    Tool execution: Get worker status.
    """
    workers = []
    for client_id, capabilities in manager.worker_capabilities.items():
        workers.append({
            "client_id": client_id,
            "status": "online", # In a real app, we'd track this more granulary
            "capabilities": capabilities
        })
    return {"workers": workers}

@router.post("/mcp/tools/list_test_results")
async def list_test_results(limit: int = 10, db: Session = Depends(database.get_db)):
    """
    Tool execution: List test results.
    """
    results = db.query(models.TestResult).order_by(models.TestResult.timestamp.desc()).limit(limit).all()
    return {"results": results}
