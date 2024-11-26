import logging
from enum import Enum
from byoeb_core.message_queue.base import BaseQueue

class Scope(Enum):
    SINGLETON = "singleton"

class QueueProviderType(Enum):
    AZURE_STORAGE_QUEUE = "azure_storage_queue"

class QueueProducerFactory:
    _az_storage_queue = None

    def __init__(
        self,
        config,
        scope
    ):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._config = config
        self._scope = scope
        
    async def __get_or_create_az_storage_queue_client(
        self
    ) -> BaseQueue:
        from byoeb_integrations.message_queue.azure.async_azure_storage_queue import AsyncAzureStorageQueue
        from azure.identity import DefaultAzureCredential
        default_credential = DefaultAzureCredential()
        if self._az_storage_queue and self._scope == Scope.SINGLETON.value:
            return self._az_storage_queue
        self._az_storage_queue = await AsyncAzureStorageQueue.aget_or_create(
            account_url=self._config["message_queue"]["azure"]["account_url"],
            queue_name=self._config["message_queue"]["azure"]["queue_bot"],
            credentials=default_credential
        )
        return self._az_storage_queue

    async def get(
        self,
        queue_provider
    ) -> BaseQueue:
        if queue_provider == QueueProviderType.AZURE_STORAGE_QUEUE.value:
            self._az_storage_queue = await self.__get_or_create_az_storage_queue_client()
            return self._az_storage_queue
        else:
            raise Exception("Invalid producer type")
        
    async def close(self):
        from byoeb_integrations.message_queue.azure.async_azure_storage_queue import AsyncAzureStorageQueue
        if isinstance(self._az_storage_queue, AsyncAzureStorageQueue):
            await self._az_storage_queue._close()
            self._logger.info("Producer Azure storage queue client closed")
        else:
            self._logger.info("Producer Azure storage queue client not initialized")