import asyncio
import hashlib
import json
import byoeb.services.chat.constants as constants
from byoeb.chat_app.configuration.config import app_config
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
        self._history_length = self._config["app"]["history_length"]

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
    
    async def get_user_activity_timestamp(
        self,
        user_id: str,
    ) -> str:
        user_collection_client = await self.__get_user_collection_client()
        query = {"_id": user_id}
        user_obj = await user_collection_client.afetch(query)
        if user_obj is None:
            return None
        user = User(**user_obj['User'])
        return user.activity_timestamp
        
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
    
    def user_activity_update_query(
        self,
        user: User,
        qa: Dict[str, Any] = None
    ):
        user_id = user.user_id
        latest_timestamp = str(int(datetime.now().timestamp()))
        update_data = {
            "$set": {
                "User.activity_timestamp": latest_timestamp
            }
        }
        if qa is None:
            return ({"_id": user_id}, update_data)
        last_convs = user.last_conversations
        if len(last_convs) >= self._history_length:
            last_convs.pop(0)
        last_convs.append(qa)
        update_data["$set"]["User.last_conversations"] = last_convs
        return ({"_id": user_id}, update_data)

    def correction_update_query(
        self,
        byoeb_user_messages: List[ByoebMessageContext],
        byoeb_expert_message: ByoebMessageContext
    ):
        for byoeb_user_message in byoeb_user_messages:
            reply_context = byoeb_user_message.reply_context
            update_id = reply_context.additional_info.get(constants.UPDATE_ID)
            reply_context.reply_id = update_id
            byoeb_user_message.reply_context = reply_context
        update_data = {
            "$set":{
                "message_data.message_context.additional_info.correction_en_text": byoeb_expert_message.reply_context.additional_info.get(constants.CORRECTION_EN),
                "message_data.message_context.additional_info.correction_source_text": byoeb_expert_message.reply_context.additional_info.get(constants.CORRECTION_SOURCE),
            }
        }
        expert_update_queries = [({"_id": byoeb_expert_message.reply_context.reply_id}, update_data)]
        user_update_queries = []
        for byoeb_user_message in byoeb_user_messages:
            update_data = {
                "$set":{
                    "message_data.message_context.additional_info.corrected_en_text": byoeb_user_message.message_context.message_english_text,
                    "message_data.message_context.additional_info.corrected_source_text": byoeb_user_message.message_context.message_source_text
                }
            }
            user_update_queries.append(({"_id": byoeb_user_message.reply_context.reply_id}, update_data))
        return expert_update_queries + user_update_queries
    
    def verification_status_update_query(
        self,
        byoeb_user_messages: List[ByoebMessageContext],
        byoeb_expert_message: ByoebMessageContext
    ):
        for byoeb_user_message in byoeb_user_messages:
            reply_context = byoeb_user_message.reply_context
            update_id = reply_context.additional_info.get(constants.UPDATE_ID)
            reply_context.reply_id = update_id
            byoeb_user_message.reply_context = reply_context
        verification_status_param = constants.VERIFICATION_STATUS
        expert_verification_status = byoeb_expert_message.reply_context.additional_info.get(verification_status_param)
        expert_modified_timestamp = byoeb_expert_message.reply_context.additional_info.get(constants.MODIFIED_TIMESTAMP)
        user_verification_status = byoeb_user_messages[0].reply_context.additional_info.get(verification_status_param)
        user_modified_timestamp = byoeb_user_messages[0].reply_context.additional_info.get(constants.MODIFIED_TIMESTAMP)
        update_data = {
            "$set":{
                "message_data.message_context.additional_info.verification_status": expert_verification_status,
                "message_data.message_context.additional_info.modified_timestamp": expert_modified_timestamp,
                "message_data.cross_conversation_context.messages_context.$[].message_context.additional_info.verification_status": user_verification_status
            }
        }
        expert_update_queries = [({"_id": byoeb_expert_message.reply_context.reply_id}, update_data)]
        user_update_queries = []
        for byoeb_user_message in byoeb_user_messages:
            update_data = {
                "$set":{
                    "message_data.message_context.additional_info.verification_status": user_verification_status,
                    "message_data.message_context.additional_info.modified_timestamp": user_modified_timestamp
                }
            }
            user_update_queries.append(({"_id": byoeb_user_message.reply_context.reply_id}, update_data))
        return expert_update_queries + user_update_queries
    
    async def execute_message_queries(
        self,
        queries: Dict[str, Any]
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
        queries: Dict[str, Any]
    ):
        user_client = await self.__get_user_collection_client()
        if queries is None or len(queries) == 0:
            return
        if "create" in queries:
            await user_client.ainsert(queries["create"])
        if "update" in queries:
            await user_client.aupdate(bulk_queries=queries["update"])
        