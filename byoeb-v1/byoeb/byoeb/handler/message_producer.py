import logging
from byoeb.factory.message_producer import QueueProducerFactory
class QueueProducerHandler:
    def __init__(
        self,
        message_producer: QueueProducerFactory
    ):
        self._logger = logging.getLogger(self.__class__.__name__)
        self.message_producer = message_producer

    async def handle(
        self,
        message
    ):
        producer_type = "azure_storage_queue"
        queue_producer = await self.message_producer.get(producer_type)
        response = await queue_producer.asend_message(message)