import logging
import asyncio
from datetime import datetime
from byoeb_core.message_queue.base import BaseQueue
from byoeb_integrations.message_queue.azure.async_azure_storage_queue import AsyncAzureStorageQueue

class QueueConsumer:

    queue: BaseQueue = None
    def __init__(
        self,
        config: dict,
        consuemr_type: str = None
    ):
        self._logger = logging.getLogger(__name__)
        self._consumer_type = consuemr_type
        self._config = config
    
    async def initialize(
        self
    ):
        if self.queue:
            self._logger.info("Queue already initialized")
            return
        if self._consumer_type == "azure_storage_queue":
            self.queue = await self.__get_or_create_az_storag_queue_client()
            if isinstance(self.queue, AsyncAzureStorageQueue):
                self._logger.info(f"Azure storage queue client created: {self.queue}")
        else:
            self._logger.error(f"Error initializing")

    async def __areceive(
        self
    ) -> list:
        messages = []
        if isinstance(self.queue, AsyncAzureStorageQueue):
            msgs = await self.queue.areceive_message(
                visibility_timeout=self._config["message_queue"]["azure"]["visibility_timeout"],
                messages_per_page=self._config["message_queue"]["azure"]["messages_per_page"]
            )
            async for msg in msgs:
                messages.append(msg)
        
        return messages

    async def __delete_message(
        self,
        messages: list,
    ):
        if isinstance(self.queue, AsyncAzureStorageQueue):
            tasks = []
            for message in messages:
                task  = self.queue.adelete_message(message)
                tasks.append(task)
            await asyncio.gather(*tasks)

    async def __get_or_create_az_storag_queue_client(
        self,
    ) -> BaseQueue:
        from azure.identity import DefaultAzureCredential
        default_credential = DefaultAzureCredential()
        if not self.queue:
            return await AsyncAzureStorageQueue.aget_or_create(
                account_url=self._config["message_queue"]["azure"]["account_url"],
                queue_name=self._config["message_queue"]["azure"]["queue_bot"],
                credentials=default_credential
            )
        return self.queue

    async def listen(
        self
    ):
        await self.initialize()
        self._logger.info(f"Queue info: {self.queue}")
        while True:
            time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._logger.info(f"Listening for messages at: {time_now}")
            messages = await self.__areceive()
            # handle messages
            self._logger.info(f"Received {len(messages)} messages")
            await self.__delete_message(messages)
            self._logger.info(f"Deleted {len(messages)} messages")
            await asyncio.sleep(2)
    
    async def close(
        self
    ):
        self._logger.info(self.queue)
        if isinstance(self.queue, AsyncAzureStorageQueue):
            await self.queue._close()
            self._logger.info("Closed the Azure storage queue client")
        else:
            self._logger.info("No queue client to close")

    
    