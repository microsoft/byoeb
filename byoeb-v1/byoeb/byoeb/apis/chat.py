import logging
import json
import asyncio
from fastapi import APIRouter, Request
from byoeb.app.configuration.singletons import (
    whatsapp_client,
    queue_producer_handler
)
# from byoeb_integrations.channel.whatsapp.meta.async_whatsapp_client import AsyncWhatsAppClient
from byoeb.app.configuration.configuration import (
    env_whatsapp_phone_number_id,
    env_whatsapp_auth_token,
    app_settings
)

CHAT_API_NAME = 'chat_api'
logging.basicConfig(level=logging.INFO)
chat_apis_router = APIRouter()
_logger = logging.getLogger(CHAT_API_NAME)

@chat_apis_router.post("/receive")
async def receive(request: Request):
    """
    Handle incoming WhatsApp messages.
    """
    body = await request.json()
    _logger.info(f"Received the request: {json.dumps(body)}")
    response = await queue_producer_handler.handle(body)
    _logger.info(f"Response: {response}")
    return {"message": "received", "status_code": 200}
