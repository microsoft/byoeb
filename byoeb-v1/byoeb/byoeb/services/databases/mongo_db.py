import asyncio
import json
from byoeb_core.models.byoeb.message_context import ByoebMessageContext
from typing import List, Dict, Any
from datetime import datetime
from byoeb_core.models.byoeb.user import User
from byoeb_core.databases.mongo_db.base import BaseDocumentCollection
from byoeb.factory import MongoDBFactory
from byoeb_integrations.databases.mongo_db.azure.async_azure_cosmos_mongo_db import AsyncAzureCosmosMongoDBCollection

class MongoDBService:

    def __init__(
        self,
        config,
        mongo_db_factory: MongoDBFactory
    ):
        self._config = config
        self._mongo_db_factory = mongo_db_factory

    async def __get_message_collection_client(
        self
    ) -> BaseDocumentCollection:
        mongo_db = await self._mongo_db_factory.get(self._config["app"]["db_provider"])
        message_collection = self._config["databases"]["mongo_db"]["message_collection"]
        message_collection_client = AsyncAzureCosmosMongoDBCollection(
            collection=mongo_db.get_collection(message_collection)
        )
        return message_collection_client
    
    async def __get_user_collection_client(
        self
    ) -> BaseDocumentCollection:
        mongo_db = await self._mongo_db_factory.get(self._config["app"]["db_provider"])
        user_collection = self._config["databases"]["mongo_db"]["user_collection"]
        user_collection_client = AsyncAzureCosmosMongoDBCollection(
            collection=mongo_db.get_collection(user_collection)
        )
        return user_collection_client

    async def get_users(
        self,
        user_ids: list
    ) -> List[User]:
        user_collection_client = await self.__get_user_collection_client()
        query = {"_id": {"$in": user_ids}}
        users_obj = await user_collection_client.afetch_all(query)
        byoeb_users = []
        for user_obj in users_obj:
            user = user_obj['User']
            byoeb_user = User(**user)
            byoeb_users.append(byoeb_user)
        return byoeb_users
    
    async def get_bot_messages(
        self,
        bot_message_ids: list
    ) -> List[ByoebMessageContext]:
        message_collection_client = await self.__get_message_collection_client()
        query = {"_id": {"$in": bot_message_ids}}
        messages_obj = await message_collection_client.afetch_all(query)
        byoeb_messages = []
        for message_obj in messages_obj:
            message = message_obj['message_data']
            byoeb_message = ByoebMessageContext(**message)
            byoeb_messages.append(byoeb_message)

        return byoeb_messages

    def message_create_queries(
        self,
        byoeb_messages: List[ByoebMessageContext]
    ) -> list:
        if len(byoeb_messages) == 0:
            return
        json_message_data = []
        for byoeb_message in byoeb_messages:
            json_message_data.append({
                "_id": byoeb_message.message_context.message_id,
                "message_data": byoeb_message.model_dump(),
                "timestamp": str(int(datetime.now().timestamp()))
            })
        return json_message_data
    
    def verification_status_update_query(
        self,
        byoeb_user_messages: List[ByoebMessageContext],
        byoeb_expert_message: ByoebMessageContext
    ):
        verification_status_param = "verification_status"
        expert_verification_status = byoeb_expert_message.reply_context.additional_info.get(verification_status_param) 
        user_verification_status = byoeb_user_messages[0].reply_context.additional_info.get(verification_status_param)
        update_data = {
            "$set":{
                "message_data.message_context.additional_info.verification_status": expert_verification_status,
                "message_data.cross_conversation_context.messages_context.$[].additional_info.verification_status": user_verification_status
            }
        }
        expert_update_queries = [({"_id": byoeb_expert_message.reply_context.reply_id}, update_data)]
        user_update_queries = []
        for byoeb_user_message in byoeb_user_messages:
            update_data = {
                "$set":{
                    "message_data.message_context.additional_info.verification_status": user_verification_status
                }
            }
            user_update_queries.append(({"_id": byoeb_user_message.reply_context.reply_id}, update_data))
        return expert_update_queries + user_update_queries
    
    async def execute_message_queries(
        self,
        queries: List[Dict[str, Any]]
    ):
        message_client = await self.__get_message_collection_client()
        if queries is None or len(queries) == 0:
            return
        if "create" in queries:
            await message_client.ainsert(queries["create"])
        if "update" in queries:
            await message_client.aupdate(bulk_queries=queries["update"])
           
    async def execute_user_queries(
        self,
        queries: List[Dict[str, Any]]
    ):
        user_client = await self.__get_user_collection_client()
        if queries is None or len(queries) == 0:
            return
        if "create" in queries:
            await user_client.ainsert(queries["create"])
        if "update" in queries:
            await user_client.aupdate(bulk_queries=queries["update"])
        