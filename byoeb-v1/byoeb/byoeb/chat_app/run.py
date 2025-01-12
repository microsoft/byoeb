import logging
import os
import asyncio
import uvicorn
from uvicorn.config import LOGGING_CONFIG
from fastapi import FastAPI
from contextlib import asynccontextmanager
from byoeb.apis.health import health_apis_router
from byoeb.apis.channel_register import register_apis_router
from byoeb.apis.chat import chat_apis_router
from byoeb.apis.user import user_apis_router

asyncio.get_event_loop().set_debug(True)
def create_app():
    """
    Creates and configures a FastAPI application.

    Returns:
        Flask: A configured FastAPI application instance.
    """

    app = FastAPI(lifespan=lifespan)
    app.include_router(health_apis_router)
    app.include_router(register_apis_router)
    app.include_router(chat_apis_router)
    app.include_router(user_apis_router)
    return app

@asynccontextmanager
async def lifespan(app: FastAPI):
    pid = os.getpid()
    print(f"FastAPI app is running with PID: {pid}")
    from byoeb.chat_app.configuration.dependency_setup import (
        channel_client_factory, 
        message_consumer,
        queue_producer_factory
    )
    await message_consumer.initialize()
    asyncio.create_task(message_consumer.listen())
    yield
    await channel_client_factory.close()
    await message_consumer.close()
    await queue_producer_factory.close()
    print("Closed all clients.")

app = create_app()
if __name__ == '__main__':
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=5000
    )