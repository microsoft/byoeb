import logging
import asyncio
from enum import Enum
from byoeb_core.databases.mongo_db.base import BaseDocumentDatabase

class Scope(Enum):
    SINGLETON = "singleton"

class MongoDBProviderType(Enum):
    AZURE_COSMOS_MONGO_DB = "azure_cosmos_mongo_db"

class MongoDBFactory:
    _az_cosmos_mongo_db: BaseDocumentDatabase = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __init__(
        self,
        config,
        scope
    ):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._config = config
        self._scope = scope

    async def get(
        self,
        db_provider
    ) -> BaseDocumentDatabase:
        if db_provider == MongoDBProviderType.AZURE_COSMOS_MONGO_DB.value:
            return await self.__get_or_create_az_cosmos_mongo_db_client()
        else:
            raise Exception("Invalid db type")
        
    async def __get_or_create_az_cosmos_mongo_db_client(
        self
    ):
        import byoeb.chat_app.configuration.config as env_config
        from byoeb_integrations.databases.mongo_db.azure.async_azure_cosmos_mongo_db import AsyncAzureCosmosMongoDB

        async with self._lock:
            if self._az_cosmos_mongo_db and self._scope == Scope.SINGLETON.value:
                return self._az_cosmos_mongo_db

            self._az_cosmos_mongo_db = AsyncAzureCosmosMongoDB(
                connection_string=env_config.env_mongo_db_connection_string,
                database_name=self._config["databases"]["mongo_db"]["database_name"],
            )
            return self._az_cosmos_mongo_db
    
    async def close(self):
        pass

