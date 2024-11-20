import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from byoeb.app.configuration.singletons import channel_register_handler

REGISTER_API_NAME = 'register_api'

register_apis_router = APIRouter()
_logger = logging.getLogger(REGISTER_API_NAME)

@register_apis_router.get("/receive")
async def register(request: Request):
    """
    Route to handle the registration process.
    """
    # print("Received the request: ", request.query_params._dict)
    _logger.debug(msg=f"Received the request: \n{request.query_params._dict}")
    response = await channel_register_handler.handle(request)
    print("Response: ", response.message)
    return int(response.message)
    # return JSONResponse(content={"message": "received"}, status_code=200)
