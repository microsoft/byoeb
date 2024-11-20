import logging
from typing import Any, Dict, List
import certifi
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection,AsyncIOMotorDatabase
from byoeb_core.databases.document_db.base import BaseDocumentDatabase, BaseDocumentCollection

class AsyncAzureCosmosMongoDB(BaseDocumentDatabase):
    _client = None
    __db = None
    __database_name = None
    def __init__(
        self,
        connection_string: str,
        database_name: str = None,
        **kwargs
    ):
        if connection_string is None:
            raise ValueError("connection_string must be provided")
        self.__logger = logging.getLogger(self.__class__.__name__)
        self.__connection_string = connection_string
        self.__initialize_client()
        if database_name is not None:
            self.get_or_create_db(database_name)

    def __initialize_client(self):
        if not AsyncAzureCosmosMongoDB._client:
            AsyncAzureCosmosMongoDB._client = AsyncIOMotorClient(
                self.__connection_string,
                tlsCAFile=certifi.where()
            )
        

    def get_db_name(self) -> str:
        return self.__database_name

    def get_or_create_db(
        self,
        db_name=None
    ) -> AsyncIOMotorDatabase:
        if self.__database_name is not None and db_name is not None:
            raise ValueError("A database already exist. If changing database, delete the existing database first or create a new instance")
        if self.__database_name is None and db_name is None:
            raise ValueError("Database name must be provided")
        else:
            self.__database_name = db_name
        if self.__db is None:
            self.__db = AsyncAzureCosmosMongoDB._client[self.__database_name]
        return self.__db
    
    def get_collection(
        self,
        collection_name: str
    ) -> AsyncIOMotorCollection:
        if self.__db is None:
            raise ValueError("Database must be initialized before operating on collection")
        return self.__db[collection_name]
    
    async def aget_collection(
        self,
        collection_name: str
    ) -> AsyncIOMotorCollection:
        raise NotImplementedError

    def delete_collection(
        self,
        collection_name: str
    ) -> Any:
        raise NotImplementedError
    
    async def adelete_collection(
        self,
        collection_name: str
    ) -> Any:
        collection = self.get_collection(collection_name)
        await collection.drop()
    
    def delete_database(self) -> Any:
        raise NotImplementedError
    
    async def adelete_database(self):
        await AsyncAzureCosmosMongoDB._client.drop_database(self.__database_name)
        self.__db = None
        self.__database_name = None
    

class AsyncAzureCosmosMongoDBCollection(BaseDocumentCollection):
    __db_client = None
    def __init__(
        self,
        collection: AsyncIOMotorCollection = None,
        collection_name: str = None,
        db_client: AsyncAzureCosmosMongoDB = None,
        **kwargs
    ):
        if collection is not None:
            self.__collection_name = collection.name
            self.__collection = collection
        elif collection_name is not None and db_client is not None:
            self.__collection_name = collection_name
            self.__collection = db_client.get_collection(collection_name)
        else:
            raise ValueError("Either collection or collection_name and db_client must be provided")

    def get_collection_name(self) -> AsyncIOMotorCollection:
        return self.__collection_name
    
    def insert(
        self,
        data: List[Dict[str, Any]],
        **kwargs
    ) -> Any:
        raise NotImplementedError

    async def ainsert(
        self,
        data: List[Dict[str, Any]],
        **kwargs
    ) -> Any:
        if self.__collection is None:
            raise ValueError("Collection is not present or deleted. Please create a new collection")
        return await self.__collection.insert_many(data)
    
    def fetch(
        self,
        query: Dict[str, Any],
        **kwargs
    ) -> Any:
        raise NotImplementedError

    async def afetch(
        self,
        query: Dict[str, Any],
        **kwargs
    ) -> Any:
        if self.__collection is None:
            raise ValueError("Collection is not present or deleted. Please create a new collection")
        return await self.__collection.find_one(query)
    
    def fetch_all(
        self,
        query: Dict[str, Any] = None,
        **kwargs
    ) -> Any:
        raise NotImplementedError
    
    async def afetch_all(
        self,
        query: Dict[str, Any] = None,
        **kwargs
    ) -> Any:
        if self.__collection is None:
            raise ValueError("Collection is not present or deleted. Please create a new collection")
        cursor = None
        if query is None:
            cursor = self.__collection.find()
        cursor = self.__collection.find(query)
        documents = await cursor.to_list(length=None)
        return documents
                  
    def update(
        self,
        query: Dict[str, Any], 
        update_data: Dict[str, Any],
        **kwargs
    ) -> Any:
        raise NotImplementedError
    
    async def aupdate(
        self,
        query: Dict[str, Any], 
        update_data: Dict[str, Any],
        **kwargs
    ) -> Any:
        if self.__collection is None:
            raise ValueError("Collection is not present or deleted. Please create a new collection")
        return await self.__collection.update_many(query, update_data)
    
    def delete(
        self, 
        query: Dict[str, Any], 
        **kwargs
    ) -> Any:
        raise NotImplementedError
    
    async def adelete(
        self, 
        query: Dict[str, Any], 
        **kwargs
    ) -> Any:
        if self.__collection is None:
            raise ValueError("Collection is not present or deleted. Please create a new collection")
        return await self.__collection.delete_many(query)
    
    def delete_collection(self) -> Any:
        raise NotImplementedError
    
    async def adelete_collection(self) -> Any:
        await self.__collection.drop()
        self.__collection = None
        self.__collection_name = None