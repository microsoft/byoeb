import logging
import asyncio
import uvicorn
from uvicorn.config import LOGGING_CONFIG
from fastapi import FastAPI
from contextlib import asynccontextmanager
from byoeb.apis.health import health_apis_router
from byoeb.apis.channel_register import register_apis_router
from byoeb.apis.chat import chat_apis_router

LOGGING_CONFIG["formatters"]["default"] = {
    "()": "uvicorn.logging.DefaultFormatter",
    "fmt": (
        "%(asctime)s | %(levelname)s | %(name)s | %(filename)s | "
        "line: %(lineno)d | thread: %(threadName)s | %(message)s"
    ),
    "use_colors": True,  # Enable colored output
}

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
    return app

@asynccontextmanager
async def lifespan(app: FastAPI):
    from byoeb.app.configuration.singletons import (
        whatsapp_client, 
        queue_consumer,
        queue_producer_factory
    )
    await queue_consumer.initialize()
    asyncio.create_task(queue_consumer.listen())
    yield
    await whatsapp_client._close()
    await queue_consumer.close()
    await queue_producer_factory.close()
    print("Closed all clients.")

app = create_app()
if __name__ == '__main__':
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=5000,
        log_level="info",
        log_config="/home/rash598/byoeb-v1/byoeb/byoeb/app/logging.yaml"
    )