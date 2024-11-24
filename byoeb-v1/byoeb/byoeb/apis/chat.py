import logging
import json
import asyncio
import byoeb.app.configuration.singletons as singletons
from fastapi import APIRouter, Request
# from byoeb_integrations.channel.whatsapp.meta.async_whatsapp_client import AsyncWhatsAppClient
from byoeb.app.configuration.config import (
    env_whatsapp_phone_number_id,
    env_whatsapp_auth_token,
    app_config
)

CHAT_API_NAME = 'chat_api'
chat_apis_router = APIRouter()
_logger = logging.getLogger(CHAT_API_NAME)

@chat_apis_router.post("/receive")
async def receive(request: Request):
    """
    Handle incoming WhatsApp messages.
    """
    body = await request.json()
    print("Received the request: ", json.dumps(body))
    _logger.info(f"Received the request: {json.dumps(body)}")
    response = await singletons.queue_producer_handler.handle(body)
    _logger.info(f"Response: {response}")
    return {"message": "received", "status_code": 200}
