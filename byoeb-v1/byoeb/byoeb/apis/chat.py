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
    responses = await dependency_setup.mongo_db_service.get_latest_bot_messages_by_timestamp(timestamp)
    byoeb_response = []
    for response in responses:
        byoeb_response.append(response.model_dump())
    return JSONResponse(
        content=byoeb_response,
        status_code=200
    )

@chat_apis_router.delete("/delete_message_collection")
async def delete_collection(
    request: Request,
):
    """
    Delete a collection from the database.
    """
    response, e = await dependency_setup.mongo_db_service.delete_message_collection()
    if response == True:
        return JSONResponse(
            content="Successfully deleted",
            status_code=200
        )
    elif response == False and e is None:
        return JSONResponse(
            content="Failed to delete",
            status_code=500
        )
    elif e is not None:
        return JSONResponse(
            content=f"Error: {e}",
            status_code=500
        )
