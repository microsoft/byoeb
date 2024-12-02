import logging
import byoeb_integrations.channel.whatsapp.validate_message as wa_validator
from typing import Any
from byoeb.factory import QueueProducerFactory
from byoeb.services.chat.message_producer import MessageProducerService
from byoeb_core.models.byoeb.response import ByoebResponseModel, ByoebStatusCodes

class QueueProducerHandler:
    def __init__(
        self,
        config,
        queue_producer_factory: QueueProducerFactory
    ):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._config = config
        self._queue_provider = config["app"]["queue_provider"]
        self.queue_producer_factory = queue_producer_factory

    async def __get_or_create_message_producer(
        self,
        message_type
    ) -> MessageProducerService:
        queue_client = await self.queue_producer_factory.get(self._queue_provider, message_type)
        return MessageProducerService(self._config, queue_client)

    async def __validate_channel_and_get_message_type(
        self,
        message
    ) -> Any:
        is_whatsapp, message_type = wa_validator.validate_whatsapp_message(message)
        if is_whatsapp:
            return "whatsapp", message_type
        return False, None
            
        
    async def handle(
        self,
        message
    ):
        channel, message_type = await self.__validate_channel_and_get_message_type(message)
        if not channel:
            return ByoebResponseModel(
                status_code=ByoebStatusCodes.BAD_REQUEST,
                message="Invalid channel"
            )
        message_producer_service = None
        try:
            message_producer_service = await self.__get_or_create_message_producer(message_type)
        except Exception as e:
            return ByoebResponseModel(
                status_code=ByoebStatusCodes.INTERNAL_SERVER_ERROR,
                message= f"Invalid producer type: {str(e)}"
            )
        
        response, err = await message_producer_service.apublish_message(message, channel)
        if err is not None:
            return ByoebResponseModel(
                status_code=ByoebStatusCodes.INTERNAL_SERVER_ERROR,
                message=err
            )
        return ByoebResponseModel(
            status_code=ByoebStatusCodes.OK,
            message=response
        )
        