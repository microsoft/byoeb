import logging
from byoeb_core.message_queue.base import BaseQueue

class QueueProducerFactory:
    _az_storage_queue = None

    def __init__(self, config):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._config = config

    async def get(
        self,
        producer_type,
        reuse_client: bool = True
    ) -> BaseQueue:
        if producer_type == "azure_storage_queue":
            return await self.__get_or_create_az_storag_queue_client(reuse_client)
        else:
            raise Exception("Invalid producer type")
        
    async def __get_or_create_az_storag_queue_client(
        self,
        reuse_client
    ) -> BaseQueue:
        from byoeb_integrations.message_queue.azure.async_azure_storage_queue import AsyncAzureStorageQueue
        from azure.identity import DefaultAzureCredential
        default_credential = DefaultAzureCredential()
        if not self._az_storage_queue or reuse_client is False:
            self._az_storage_queue = await AsyncAzureStorageQueue.aget_or_create(
                account_url=self._config["azure"]["storage_account"]["account_url"],
                queue_name=self._config["azure"]["storage_account"]["queue_bot"],
                credentials=default_credential
            )
        return self._az_storage_queue

    async def close(self):
        from byoeb_integrations.message_queue.azure.async_azure_storage_queue import AsyncAzureStorageQueue
        if isinstance(self._az_storage_queue, AsyncAzureStorageQueue):
            await self._az_storage_queue._close()
            self._logger.info("Producer Azure storage queue client closed")
        else:
            self._logger.info("Producer Azure storage queue client not initialized")