from byoeb_core.models.byoeb.user import User
from byoeb_core.databases.mongo_db.base import BaseDocumentCollection
from byoeb.factory import MongoDBFactory
from byoeb_integrations.databases.mongo_db.azure.async_azure_cosmos_mongo_db import AsyncAzureCosmosMongoDBCollection

class BaseMongoDBService:
    """Base service class for MongoDB operations."""

    def __init__(self, config, mongo_db_factory: MongoDBFactory):
        self._config = config
        self._mongo_db_factory = mongo_db_factory

    async def _get_collection_client(self, collection_name: str) -> BaseDocumentCollection:
        """Get the MongoDB collection client based on the collection name."""
        mongo_db = await self._mongo_db_factory.get(self._config["app"]["db_provider"])
        collection = mongo_db.get_collection(collection_name)
        return AsyncAzureCosmosMongoDBCollection(collection=collection)