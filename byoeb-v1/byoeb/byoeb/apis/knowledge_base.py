import logging
import json
import byoeb.chat_app.configuration.dependency_setup as dependency_setup
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

KB_API_NAME = 'kb_api'

kb_apis_router = APIRouter()
_logger = logging.getLogger(KB_API_NAME)

@kb_apis_router.post("/add_document")
async def add_document(request: Request):
    body = await request.json()
    response = await dependency_setup.users_handler.aregister(body)
    print("Response: ", response.message)
    return JSONResponse(
        content=response.message,
        status_code=response.status_code
    )

@kb_apis_router.delete("/delete_document")
async def delete_document(request: Request):
    body = await request.json()
    response = await dependency_setup.users_handler.adelete(body)
    return JSONResponse(
        content=response.message,
        status_code=response.status_code
    )

@kb_apis_router.post("/replace_document")
async def replace_document(request: Request):
    body = await request.json()
    response = await dependency_setup.users_handler.aget(body)
    return JSONResponse(
        content=response.message,
        status_code=response.status_code
    )