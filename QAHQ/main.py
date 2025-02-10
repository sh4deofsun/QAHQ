"""
file handler websocket or rest api
"""
# standard library
import time

from typing import Annotated

# from pydantic import BaseModel, Field, EmailStr
from fastapi import FastAPI, Request, UploadFile, File, Body, Header, Response, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.exceptions import HTTPException

from Applications.TestCounterSingleton import test_counter

app = FastAPI(
    title="QAHQ",
    description="QAHQ",
    version="0.0.1",
    contact={
        "name": "BY",
        },
)

app.include_router(router=test_counter.router,
                   tags=["Robot Framework"])

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """
    middleware, run on every http request
    for now just add processtime to respopnse header
    """
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["Signature"] = "SQAA-T64572-BY"
    return response


@app.get("/")
def read_root():
    """
    main root
    """
    return {"Hello": "World"}

@app.post("/mirror/", response_model=None)
async def mirror(msg : Annotated[str, Body(embed=True)]) -> JSONResponse:
    return JSONResponse(content={"Your message" : msg})

favicon_path = "favicon.ico"
@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse(favicon_path)
