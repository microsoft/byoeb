import logging
import asyncio
import byoeb.utils.utils as utils
from datetime import datetime
from byoeb_core.message_queue.base import BaseQueue
from byoeb.factory import ChannelClientFactory
from byoeb.services.chat.message_consumer import MessageConsmerService
from byoeb.services.databases.mongo_db import MongoDBService
from byoeb_integrations.message_queue.azure.async_azure_storage_queue import AsyncAzureStorageQueue

class QueueConsumer:

    _az_storage_queue: BaseQueue = None
    def __init__(
        self,
        account_url: str,
        queue_name: str,
        config: dict,
        mongo_db_service: MongoDBService,
        channel_client_factory: ChannelClientFactory,
        consuemr_type: str = None,
    ):
        self._logger = logging.getLogger(__name__)
        self._consumer_type = consuemr_type
        self._account_url = account_url
        self._queue_name = queue_name
        self._config = config
        self._mongo_db_service = mongo_db_service
        self._channel_client_factory = channel_client_factory
    
    async def __get_or_create_az_storage_queue_client(
        self,
    ) -> BaseQueue:
        from azure.identity import DefaultAzureCredential
        default_credential = DefaultAzureCredential()
        if not self._az_storage_queue:
            self._az_storage_queue = await AsyncAzureStorageQueue.aget_or_create(
                account_url=self._account_url,
                queue_name=self._queue_name,
                credentials=default_credential
            )
        return self._az_storage_queue
    
    async def initialize(
        self
    ):
        if self._az_storage_queue:
            self._logger.info("Queue already initialized")
            return
        if self._consumer_type == "azure_storage_queue":
            self._az_storage_queue = await self.__get_or_create_az_storage_queue_client()
            if isinstance(self._az_storage_queue, AsyncAzureStorageQueue):
                self._logger.info(f"Azure storage queue client created: {self._az_storage_queue}")
        else:
            self._logger.error(f"Error initializing")

    async def __areceive(
        self
    ) -> list:
        messages = []
        if isinstance(self._az_storage_queue, AsyncAzureStorageQueue):
            msgs = await self._az_storage_queue.areceive_message(
                visibility_timeout=self._config["message_queue"]["azure"]["visibility_timeout"],
                messages_per_page=self._config["message_queue"]["azure"]["messages_per_page"],
                max_messages=self._config["app"]["batch_size"]
            )
            async for msg in msgs:
                messages.append(msg)
        
        return messages

    async def __delete_message(
        self,
        messages: list,
    ):
        if isinstance(self._az_storage_queue, AsyncAzureStorageQueue):
            tasks = []
            for message in messages:
                task  = self._az_storage_queue.adelete_message(message)
                tasks.append(task)
            await asyncio.gather(*tasks)

    async def listen(
        self
    ):
        await self.initialize()
        message_consumer_svc = MessageConsmerService(
            config=self._config,
            mongo_db_service=self._mongo_db_service,
            channel_client_factory=self._channel_client_factory
        )
        self._logger.info(f"Queue info: {self._az_storage_queue}")
        while True:
            time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._logger.info(f"Listening for messages at: {time_now}")
            start_time = datetime.now()
            messages = await self.__areceive()
            message_content = []
            for message in messages:
                message_content.append(message.content)
            if len(messages) == 0:
                self._logger.info("No messages received")
                await asyncio.sleep(2)
                continue
            try:
                self._logger.info(f"Received {len(messages)} messages")
                successfully_processed_messages =  await message_consumer_svc.consume(message_content)
                utils.log_to_text_file(f"Successfully processed {len(successfully_processed_messages)} messages")
                processed_ids = {message.message_context.message_id for message in successfully_processed_messages}
                remove_messages = [msg for msg in messages if any(processed_id in msg.content for processed_id in processed_ids)]
                await self.__delete_message(remove_messages)
                self._logger.info(f"Deleted {len(remove_messages)} messages")
            except Exception as e:
                self._logger.error(f"Error consuming messages: {e}")
            end_time = datetime.now()
            duration = (end_time - start_time).seconds
            self._logger.info(f"Processing time: {duration} seconds")
            utils.log_to_text_file(f"Processed {len(messages)} message in: {duration} seconds")
            await asyncio.sleep(2)
    
    async def close(
        self
    ):
        self._logger.info(self._az_storage_queue)
        if isinstance(self._az_storage_queue, AsyncAzureStorageQueue):
            await self._az_storage_queue._close()
            self._logger.info("Closed the Azure storage queue client")
        else:
            self._logger.info("No queue client to close")  