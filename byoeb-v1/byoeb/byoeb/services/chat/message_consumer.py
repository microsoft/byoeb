import logging
import asyncio
import json
import hashlib
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List
from byoeb.factory import MongoDBFactory, ChannelClientFactory
from byoeb.app.configuration.config import bot_config
from byoeb_core.models.byoeb.user import User
from byoeb_integrations.databases.mongo_db.azure.async_azure_cosmos_mongo_db import AsyncAzureCosmosMongoDBCollection
from byoeb_core.models.byoeb.message_context import ByoebMessageContext

class Conversation(BaseModel):
    user_message: Optional[ByoebMessageContext]
    bot_message: Optional[ByoebMessageContext]
    user: User

class MessageConsmerService:
    def __init__(
        self,
        config,
        mongo_db_facory: MongoDBFactory,
        channel_client_factory: ChannelClientFactory
    ):
        self._config = config
        self._logger = logging.getLogger(self.__class__.__name__)
        self._mongo_db_facory = mongo_db_facory
        self._channel_client_factory = channel_client_factory
        self._regular_user_type = bot_config["regular"]["user_type"]
        self._expert_user_type = bot_config["expert"]["user_type"]

    async def __get_message_collection_client(
        self
    ):
        mongo_db = await self._mongo_db_facory.get(self._config["app"]["db_provider"])
        message_collection = self._config["databases"]["mongo_db"]["message_collection"]
        message_collection_client = AsyncAzureCosmosMongoDBCollection(
            collection=mongo_db.get_collection(message_collection)
        )
        return message_collection_client
    
    async def __get_user_collection_client(
        self
    ):
        mongo_db = await self._mongo_db_facory.get(self._config["app"]["db_provider"])
        user_collection = self._config["databases"]["mongo_db"]["user_collection"]
        user_collection_client = AsyncAzureCosmosMongoDBCollection(
            collection=mongo_db.get_collection(user_collection)
        )
        return user_collection_client

    async def __get_users(
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
    
    async def __get_bot_messages(
        self,
        bot_message_ids: list
    ) -> List[ByoebMessageContext]:
        message_collection_client = await self.__get_message_collection_client()
        query = {"_id": {"$in": bot_message_ids}}
        messages = await message_collection_client.afetch_all(query)
        byoeb_messages = []
        for message in messages:
            byoeb_message = ByoebMessageContext(**message)
            byoeb_messages.append(byoeb_message)

        return byoeb_messages

    # TODO: Hash can be used or better way to get user by phone number
    async def __get_user(
        self,
        users: List[User],
        phone_number_id,

    ) -> User:
        return next((user for user in users if user.phone_number_id == phone_number_id), None)
    
    async def __get_bot_message(
        self,
        messages: List[ByoebMessageContext],
        reply_id
    ) -> ByoebMessageContext:
        return next(
            (
                message for message in messages
                if message.reply_context is not None
                and message.reply_context.reply_id == reply_id
            ),
            None
        )

    async def __create_conversations(
        self,
        messages: List[ByoebMessageContext]
    ) -> List[ByoebMessageContext]:
        phone_numbers = list(set([message.user.phone_number_id for message in messages]))
        user_ids = list(set([hashlib.md5(number.encode()).hexdigest() for number in phone_numbers]))
        byoeb_users = await self.__get_users(user_ids)
        bot_message_ids = list(
            set(message.reply_context.reply_id for message in messages if not message.reply_context.reply_id)
        )
        bot_messages = await self.__get_bot_messages(bot_message_ids)
        conversations = []
        for message in messages:
            user_task = self.__get_user(byoeb_users,message.user.phone_number_id)
            bot_message_task = self.__get_bot_message(bot_messages, message.reply_context.reply_id)
            user, bot_message = await asyncio.gather(user_task, bot_message_task)
            conversation = ByoebMessageContext.model_validate(message)
            conversation.user = user
            if bot_message is None:
                conversations.append(conversation)
                continue
            conversation.reply_context.reply_id = bot_message.message_context.message_id
            conversation.reply_context.reply_type = bot_message.message_context.message_type
            conversation.cross_conversation_id = bot_message.cross_conversation_id
            conversation.cross_conversation_context = bot_message.cross_conversation_context
            conversations.append(conversation)
        return conversations
    
    async def __write_to_db(
        self,
        db_entries: List[ByoebMessageContext]
    ):
        message_collection_client = await self.__get_message_collection_client()
        json_message_data = []
        for db_entry in db_entries:
            json_message_data.append({
                "_id": db_entry.message_context.message_id,
                "message_data": db_entry.model_dump(),
                "timestamp": str(int(datetime.now().timestamp()))
            })
        await message_collection_client.ainsert(json_message_data)
        
    async def consume(
        self,
        messages: list
    ):
        byoeb_messages = []
        for message in messages:
            json_message = json.loads(message)
            byoeb_message = ByoebMessageContext.model_validate(json_message)
            byoeb_messages.append(byoeb_message)
        conversations = await self.__create_conversations(byoeb_messages)
        task = []
        for conversation in conversations:
            if conversation.user.user_type == self._regular_user_type:
                task.append(self.__process_byoebuser_conversation(conversation))
            elif conversation.user.user_type == self._expert_user_type:
                task.append(self.__process_byoebexpert_conversation(conversation))
        results = await asyncio.gather(*task)
        db_entries = [entry for result in results for entry in result]
        await self.__write_to_db(db_entries)

    async def __process_byoebuser_conversation(
        self,
        byoeb_message: ByoebMessageContext
    ):
        from byoeb.app.configuration.dependency_setup import byoeb_user_process
        # print("Process user message ", byoeb_message)
        self._logger.info(f"Process user message: {byoeb_message}")
        return await byoeb_user_process.handle([byoeb_message])

    async def __process_byoebexpert_conversation(
        self,
        byoeb_message: ByoebMessageContext
    ):
        print("Process expert message ", byoeb_message)
        self._logger.info(f"Process expert message: {byoeb_message}")
        channel_client = self._channel_client_factory.get(byoeb_message.channel_type)