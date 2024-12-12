import logging
import asyncio
from enum import Enum
from byoeb_core.message_queue.base import BaseQueue

class Scope(Enum):
    SINGLETON = "singleton"

class QueueProviderType(Enum):
    AZURE_STORAGE_QUEUE = "azure_storage_queue"

class QueueProducerFactory:
    _az_storage_queues = {}
    _locks = {}

    def __init__(
        self,
        config,
        scope
    ):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._config = config
        self._scope = scope
        
    async def __get_or_create_az_storage_queue_client(
        self,
        message_type
    ) -> BaseQueue:
        from byoeb_integrations.message_queue.azure.async_azure_storage_queue import AsyncAzureStorageQueue
        from azure.identity import DefaultAzureCredential
        if message_type not in self._locks:
            self._locks[message_type] = asyncio.Lock()
        async with self._locks[message_type]:
            if self._az_storage_queues.get(message_type) and self._scope == Scope.SINGLETON.value:
                return self._az_storage_queues[message_type]
            default_credential = DefaultAzureCredential()
            if message_type == "status":
                self._az_storage_queues[message_type] = await AsyncAzureStorageQueue.aget_or_create(
                    account_url=self._config["message_queue"]["azure"]["account_url"],
                    queue_name=self._config["message_queue"]["azure"]["queue_status"],
                    credentials=default_credential
                )
            else:
                self._az_storage_queues[message_type] = await AsyncAzureStorageQueue.aget_or_create(
                    account_url=self._config["message_queue"]["azure"]["account_url"],
                    queue_name=self._config["message_queue"]["azure"]["queue_bot"],
                    credentials=default_credential
                )

            return self._az_storage_queues[message_type]

    async def __close_az_storage_queue_client(
        self,
    ):
        from byoeb_integrations.message_queue.azure.async_azure_storage_queue import AsyncAzureStorageQueue
        for key, value in self._az_storage_queues.items():
            if isinstance(value, AsyncAzureStorageQueue):
                await value._close()
                self._logger.info(f"Producer Azure storage queue client closed: {key}")
            else:
                self._logger.info(f"Producer Azure storage queue client not initialized: {key}")

    async def get(
        self,
        queue_provider,
        message_type,
    ) -> BaseQueue:
        if queue_provider == QueueProviderType.AZURE_STORAGE_QUEUE.value:
            return await self.__get_or_create_az_storage_queue_client(message_type)
        else:
            raise Exception("Invalid producer type")
        
    async def close(self):
        await self.__close_az_storage_queue_client()