from byoeb_integrations.message_queue.azure.async_azure_storage_queue import AsyncAzureStorageQueue
import asyncio
import pytest
import logging
from azure.identity import DefaultAzureCredential

# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s %(levelname)s %(name)s %(filename)s %(lineno)d %(threadName)s : %(message)s'
# )

@pytest.fixture
def event_loop():
    """Create and provide a new event loop for each test."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

async def aazure_queue_ops():
    account_url = ""
    queue_name = "mybyoebqueue"
    default_credential = DefaultAzureCredential()
    async_storage_queue: AsyncAzureStorageQueue = await AsyncAzureStorageQueue.aget_or_create(
        queue_name=queue_name,
        account_url=account_url,
        credentials=default_credential
    )
    i = 0
    while i < 3:
        message = "Hello World"
        await async_storage_queue.asend_message(message)
        rmessage = await async_storage_queue.areceive_message(
            messages_per_page=2,
        )
        async for msg in rmessage:
            print(msg)
            await async_storage_queue.adelete_message(msg)
            assert msg is not None
            assert msg.content == message
        
        i += 1
    
    await async_storage_queue._close()
        
def test_async_azure_queue(event_loop):
    event_loop.run_until_complete(aazure_queue_ops())