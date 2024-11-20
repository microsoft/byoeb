import os
import logging
from byoeb_integrations.channel.whatsapp.register import RegisterWhatsapp
from byoeb.app.configuration.configuration import env_whatsapp_token

class ChannelRegisterAppFactory:
    def __init__(self):
        self._logger = logging.getLogger(__name__)

    def get(
        self,
        channel_type: str
    ):
        if channel_type == 'whatsapp':
            return RegisterWhatsapp(env_whatsapp_token)
        else:
            self._logger.error(f"Invalid channel type: {channel_type}")
            raise ValueError(f"Invalid channel type: {channel_type}")