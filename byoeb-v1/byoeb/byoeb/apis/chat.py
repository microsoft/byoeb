import logging
import json
import asyncio
import byoeb.chat_app.configuration.dependency_setup as dependency_setup
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

CHAT_API_NAME = 'chat_api'
chat_apis_router = APIRouter()
_logger = logging.getLogger(CHAT_API_NAME)

@chat_apis_router.post("/receive")
async def receive(request: Request):
    """
    Handle incoming WhatsApp messages.
    """
    body = await request.json()
    # print("Received the request: ", json.dumps(body))
    _logger.info(f"Received the request: {json.dumps(body)}")
    response = await dependency_setup.message_producer_handler.handle(body)
    _logger.info(f"Response: {response}")
    return JSONResponse(
        content=response.message,
        status_code=response.status_code
    )
