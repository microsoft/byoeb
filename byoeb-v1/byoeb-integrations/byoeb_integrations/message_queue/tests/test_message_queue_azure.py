import asyncio
import pytest
import logging
import os
from byoeb_integrations.message_queue.azure.async_azure_storage_queue import AsyncAzureStorageQueue
from azure.identity import DefaultAzureCredential
from byoeb_integrations import test_environment_path
from dotenv import load_dotenv

load_dotenv(test_environment_path)

# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s %(levelname)s %(name)s %(filename)s %(lineno)d %(threadName)s : %(message)s'
# )

MESSAGE_QUEUE_ACCOUNT_URL = os.getenv("MESSAGE_QUEUE_ACCOUNT_URL")
MESSAGE_QUEUE_BOT = os.getenv("MESSAGE_QUEUE_BOT")
MESSAGE_QUEUE_CHANNEL = os.getenv("MESSAGE_QUEUE_CHANNEL")
MESSAGE_QUEUE_MESSAGES_PER_PAGE = os.getenv("MESSAGE_QUEUE_MESSAGES_PER_PAGE")
MESSAGE_QUEUE_VISIBILITY_TIMEOUT = os.getenv("MESSAGE_QUEUE_VISIBILITY_TIMEOUT")

@pytest.fixture
def event_loop():
    """Create and provide a new event loop for each test."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

async def aazure_queue_ops():
    account_url = MESSAGE_QUEUE_ACCOUNT_URL
    queue_name = MESSAGE_QUEUE_BOT
    default_credential = DefaultAzureCredential()
    async_storage_queue: AsyncAzureStorageQueue = await AsyncAzureStorageQueue.aget_or_create(
        queue_name=queue_name,
        account_url=account_url,
        credentials=default_credential
    )
    i = 0
    while i < 3:
        message = "Hello World"
        results = await async_storage_queue.asend_message(message)
        print(results)
        rmessage = await async_storage_queue.areceive_message(
            messages_per_page=MESSAGE_QUEUE_MESSAGES_PER_PAGE,
        )
        async for msg in rmessage:
            # print(msg)
            await async_storage_queue.adelete_message(msg)
            assert msg is not None
            assert msg.content == message
        
        i += 1
    
    await async_storage_queue._close()
        
def test_async_azure_queue(event_loop):
    event_loop.run_until_complete(aazure_queue_ops())

if __name__ == "__main__":
    asyncio.run(aazure_queue_ops())