import logging
from byoeb.factory import QueueProducerFactory

class QueueProducerHandler:
    def __init__(
        self,
        queue_provider: str,
        queue_producer_factory: QueueProducerFactory
    ):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._queue_provider = queue_provider
        self.queue_producer_factory = queue_producer_factory

    async def handle(
        self,
        message
    ):
        queue_producer = None
        try:
            queue_producer = await self.queue_producer_factory.get(self._queue_provider)
        except:
            raise Exception("Invalid producer type")
        response = await queue_producer.asend_message(message)
        
        