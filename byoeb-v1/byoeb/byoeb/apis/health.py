import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

HEALTH_API_NAME = 'health_api'

health_apis_router = APIRouter()
_logger = logging.getLogger(HEALTH_API_NAME)

@health_apis_router.get("/")
async def webhook():
    """
    Health check route to confirm the bot is running.
    """
    _logger.debug("Request for index page received")
    return JSONResponse(content="Chat bot is running", status_code=200)