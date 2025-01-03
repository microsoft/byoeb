import logging
import os
import asyncio
import uvicorn
from uvicorn.config import LOGGING_CONFIG
from fastapi import FastAPI
from contextlib import asynccontextmanager
from byoeb.apis.knowledge_base import kb_apis_router

asyncio.get_event_loop().set_debug(True)
def create_app():
    """
    Creates and configures a FastAPI application.

    Returns:
        Flask: A configured FastAPI application instance.
    """

    app = FastAPI()
    app.include_router(kb_apis_router)
    return app

app = create_app()
if __name__ == '__main__':
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=5000
    )