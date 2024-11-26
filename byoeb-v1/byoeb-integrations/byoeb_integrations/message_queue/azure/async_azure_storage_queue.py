import asyncio
import logging
from enum import Enum
from typing import Any
from byoeb_core.message_queue.base import BaseQueue
from azure.storage.queue.aio import QueueClient
from azure.core.exceptions import ResourceExistsError

class AzureStorageQueueParamsEnum(Enum):
    TIME_TO_LIVE = "time_to_live"
    VISIBILITY_TIMEOUT = "visibility_timeout"
    MESSAGES_PER_PAGE = "messages_per_page"
 
class AsyncAzureStorageQueue(BaseQueue):
    __DEFAULT_TIME_TO_LIVE = 120
    __VISIBILITY_TIMEOUT = 5
    __MESSAGES_PER_PAGE = 1

    def __init__(
        self,
        queue_name: str,
        account_url: str,
        credentials: None,
        connection_string: str = None,
        **kwargs
    ):
        self.__logger = logging.getLogger(self.__class__.__name__)
        if queue_name is None:
            raise ValueError("queue_name must be provided")
        if credentials is not None and account_url is not None:
            self.__queue_client = QueueClient(
                account_url=account_url,
                queue_name=queue_name,
                credential=credentials
            )
        elif connection_string is not None:
            self.__queue_client = QueueClient.from_connection_string(
                connection_string=connection_string,
                queue_name=queue_name
            )
        else:
            raise ValueError("Either account url and credentials or connection_string must be provided")
        self.__queue_name = queue_name

    @classmethod
    async def aget_or_create(
        cls,
        queue_name: str,
        account_url: str = None,
        credentials = None,
        connection_string: str = None,
        **kwargs
    ) -> Any:
        queue = cls(
            queue_name=queue_name,
            account_url=account_url,
            credentials=credentials,
            connection_string=connection_string,
            **kwargs
        )
        await queue.___try_create_queue()
        return queue
    
    async def ___try_create_queue(self):
        try:
            await self.__queue_client.create_queue()
        except ResourceExistsError:
            self.__logger.info(f"Queue {self.__queue_name} already exists")
        except Exception as e:
            raise e
        
    async def asend_message(
        self,
        message,
        **kwargs
    ) -> Any:
        time_to_live = kwargs.get(
            AzureStorageQueueParamsEnum.TIME_TO_LIVE.value,
            self.__DEFAULT_TIME_TO_LIVE
        )
        return await self.__queue_client.send_message(
            message,
            time_to_live=time_to_live
        )

    async def areceive_message(
        self,
        **kwargs
    ) -> Any:
        visibility_timeout = kwargs.get(
            AzureStorageQueueParamsEnum.VISIBILITY_TIMEOUT.value,
            self.__VISIBILITY_TIMEOUT
        )
        messages_per_page = kwargs.get(
            AzureStorageQueueParamsEnum.MESSAGES_PER_PAGE.value,
            self.__MESSAGES_PER_PAGE
        )
        messages = self.__queue_client.receive_messages(
            visibility_timeout=visibility_timeout,
            messages_per_page=messages_per_page
        )
        return messages
        
    async def adelete_message(
        self,
        message,
        **kwargs
    ) -> Any:
        await self.__queue_client.delete_message(message)

    def send_message(
        self,
        message,
        **kwargs
    ) -> Any:
        raise NotImplementedError
    
    def receive_message(
        self,
        **kwargs
    ) -> Any:
        raise NotImplementedError
    
    def delete_message(
        self,
        message,
        **kwargs
    ) -> Any:
        raise NotImplementedError
    
    def get_azure_queue_client(self):
        return self.__queue_client
    
    async def __aenter__(self):
        return await self.__queue_client.__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.__queue_client.__aexit__(exc_type, exc_val, exc_tb)
        self.__logger.info(f"Queue {self.__queue_name} closed")

    async def _close(self):
        await self.__queue_client.close()
        self.__queue_client = None
        self.__logger.info(f"Queue {self.__queue_name} closed")

    # def __del__(self):
    #     loop = asyncio.get_event_loop()
    #     if loop.is_running():
    #         # If the loop is running, create a future and wait for it
    #         self.__logger.info(f"Closing queue {self.__queue_name}")
    #         future = asyncio.ensure_future(
    #             self.__queue_client.close(),
    #             loop=loop
    #         ).__await__()
    #     else:
    #         # If no loop is running, use asyncio.run
    #         result = asyncio.run(self.__queue_client.close())
    #     self.__logger.info(f"Queue {self.__queue_name} closed")