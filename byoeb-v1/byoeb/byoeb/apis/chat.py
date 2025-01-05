import logging
import json
import byoeb.chat_app.configuration.dependency_setup as dependency_setup
from fastapi import APIRouter, Request, Query
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

@chat_apis_router.get("/get_bot_messages")
async def get_bot_messages(
    request: Request, 
    timestamp: str = Query(..., description="Unix timestamp as a string")
):
    """
    Get all messages for a specific BO.
    """
    response = await dependency_setup.mongo_db_service.get_bot_messages(timestamp)
    _logger.info(f"Response: {response}")
    return JSONResponse(
        content="sucess",
        status_code="200"
    )
