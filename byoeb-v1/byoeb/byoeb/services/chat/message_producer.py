import logging
from byoeb_core.models.byoeb.message_status import ByoebMessageStatus
from byoeb_core.models.byoeb.message_context import ByoebMessageContext
from byoeb_core.message_queue.base import BaseQueue

class MessageProducerService:
    def __init__(
        self,
        config,
        queue_client: BaseQueue,
    ):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._config = config
        self.__queue_client = queue_client

    def __convert_whatsapp_to_byoeb_message(
        self,
        message
    ) -> ByoebMessageContext:
        import byoeb_integrations.channel.whatsapp.validate_message as wa_validator
        import byoeb_integrations.channel.whatsapp.convert_message as wa_converter
        _, message_type = wa_validator.validate_whatsapp_message(message)
        if message_type == "status":
            return message
        byoeb_message = wa_converter.convert_whatsapp_to_byoeb_message(message, message_type)
        return byoeb_message

    async def apublish_message(
        self,
        message,
        channel
    ):
        byoeb_message: ByoebMessageContext = None
        if channel == "whatsapp":
            byoeb_message = self.__convert_whatsapp_to_byoeb_message(message)
        if byoeb_message is None or byoeb_message is False:
            return None, "Invalid message"
        try:
            result = await self.__queue_client.asend_message(
                byoeb_message.model_dump_json(),
                time_to_live=self._config["message_queue"]["azure"]["time_to_live"])
            self._logger.info(f"Message sent: {result}")
            print(f"Message sent: {result}")
            return f"Published successfully {result.id}", None
        except Exception as e:
            return None, e