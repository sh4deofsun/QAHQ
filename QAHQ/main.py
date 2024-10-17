"""
file handler websocket or rest api
"""
import time
from typing import Annotated
from pydantic import BaseModel, Field, EmailStr
from fastapi import FastAPI, Request, UploadFile, File, Body, Header, Response, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.exceptions import HTTPException


app = FastAPI()


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

@app.post("/uploadfile/")
async def create_upload_file(file: Annotated[UploadFile | None, File()] = None):
    if not file:
        # return {"message": "No upload file sent"}
        return HTTPException(detail={'message': 'There was no file.'}, status_code=400)
    else:
        return {"filename": file.filename}