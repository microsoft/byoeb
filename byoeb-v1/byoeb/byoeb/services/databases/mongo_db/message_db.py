import byoeb.services.chat.constants as constants
from datetime import datetime
from typing import List, Dict, Any
from byoeb.factory import MongoDBFactory
from byoeb.services.databases.mongo_db.base import BaseMongoDBService
from byoeb_core.models.byoeb.message_context import ByoebMessageContext
from byoeb_integrations.databases.mongo_db.azure.async_azure_cosmos_mongo_db import AsyncAzureCosmosMongoDBCollection

class MessageMongoDBService(BaseMongoDBService):
    """Service class for message-related MongoDB operations."""

    def __init__(self, config, mongo_db_factory: MongoDBFactory):
        super().__init__(config, mongo_db_factory)
        self.collection_name = self._config["databases"]["mongo_db"]["message_collection"]

    async def get_bot_messages(self, bot_message_ids: List[str]) -> List[ByoebMessageContext]:
        """Fetch multiple bot messages from the database."""
        message_collection_client = await self._get_collection_client(self.collection_name)
        messages_obj = await message_collection_client.afetch_all({"_id": {"$in": bot_message_ids}})
        return [ByoebMessageContext(**msg_obj["message_data"]) for msg_obj in messages_obj]

    async def get_latest_bot_messages_by_timestamp(self, timestamp: str):
        """Fetch bot messages with timestamps greater than the given timestamp."""
        message_collection_client = await self._get_collection_client(self.collection_name)
        messages_obj = await message_collection_client.afetch_all({"timestamp": {"$gt": timestamp}})
        return [ByoebMessageContext(**msg_obj["message_data"]) for msg_obj in messages_obj]

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
    
    def message_create_queries(self, byoeb_messages: List[ByoebMessageContext]) -> List[Dict[str, Any]]:
        """Generate create queries for messages."""
        if not byoeb_messages:
            return []
        return [
            {
                "_id": message.message_context.message_id,
                "message_data": message.model_dump(),
                "timestamp": str(int(datetime.now().timestamp())),
            }
            for message in byoeb_messages
        ]
    
    def aggregate_queries(
        self,
        results: List[Dict[str, Any]]
    ):
        new_message_queries = {
            constants.CREATE: [],
            constants.UPDATE: [],
        }
        for queries, _, err in results:
            if err is not None or queries is None:
                continue
            message_queries = queries.get(constants.MESSAGE_DB_QUERIES, {})
            if message_queries is not None and message_queries != {}:
                message_create_queries = message_queries.get(constants.CREATE,[])
                message_update_queries = message_queries.get(constants.UPDATE,[])
                new_message_queries[constants.CREATE].extend(message_create_queries)
                new_message_queries[constants.UPDATE].extend(message_update_queries)
        
        return new_message_queries
    
    async def execute_queries(self, queries: Dict[str, Any]):
        """Execute message database queries."""
        if not queries:
            return

        message_client = await self._get_collection_client(self.collection_name)
        if queries.get("create"):
            await message_client.ainsert(queries["create"])
        if queries.get("update"):
            await message_client.aupdate(bulk_queries=queries["update"])

    async def delete_message_collection(self):
        """Delete the message collection."""
        try:
            message_client = await self._get_collection_client(self.collection_name)
            if isinstance(message_client, AsyncAzureCosmosMongoDBCollection):
                await message_client.adelete_collection()
                return True, None
            return False, None
        except Exception as e:
            return False, e