import os
import logging
from enum import Enum
from byoeb_integrations.channel.whatsapp.register import RegisterWhatsapp
from byoeb.chat_app.configuration.config import (
    env_whatsapp_token,
    env_whatsapp_phone_number_id,
    env_whatsapp_auth_token
)
from byoeb_integrations.channel.whatsapp.meta.async_whatsapp_client import AsyncWhatsAppClient

class ChannelType(Enum):
    WHATSAPP = 'whatsapp'

class ChannelRegisterFactory:
    def __init__(self):
        self._logger = logging.getLogger(__name__)

    def get(
        self,
        channel_type: str
    ):
        if channel_type == ChannelType.WHATSAPP.value:
            return RegisterWhatsapp(env_whatsapp_token)
        else:
            self._logger.error(f"Invalid channel type: {channel_type}")
            raise ValueError(f"Invalid channel type: {channel_type}")
    

class ChannelClientFactory:
    _whatsapp_client = None

    def __init__(
        self,
        config
    ):
        self._logger = logging.getLogger(__name__)
        self._config = config

    def __get_whatsapp_client(
        self
    ) -> AsyncWhatsAppClient:
        if self._whatsapp_client is None:
            self._whatsapp_client = AsyncWhatsAppClient(
                phone_number_id=env_whatsapp_phone_number_id,
                bearer_token=env_whatsapp_auth_token,
                reuse_client=self._config["channel"]["whatsapp"]["reuse_client"]
            )
        return self._whatsapp_client
    def get(
        self,
        channel_type: str
    ):
        if channel_type == ChannelType.WHATSAPP.value:
            return self.__get_whatsapp_client()
        else:
            self._logger.error(f"Invalid channel type: {channel_type}")
            raise ValueError(f"Invalid channel type: {channel_type}")
    
    async def close(self):
        if isinstance(self._whatsapp_client, AsyncWhatsAppClient):
            await self._whatsapp_client._close()