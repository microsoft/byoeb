import logging
import asyncio
import json
import hashlib
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List
from byoeb.models.message_category import MessageCategory
from byoeb.factory import MongoDBFactory, ChannelClientFactory
from byoeb.app.configuration.config import bot_config
from byoeb_core.models.byoeb.user import User
from byoeb.services.databases.mongo_db import MongoDBService
from byoeb_core.models.byoeb.message_context import ByoebMessageContext

class Conversation(BaseModel):
    user_message: Optional[ByoebMessageContext]
    bot_message: Optional[ByoebMessageContext]
    user: User

class MessageConsmerService:
    def __init__(
        self,
        config,
        mongo_db_service: MongoDBService,
        channel_client_factory: ChannelClientFactory
    ):
        self._config = config
        self._logger = logging.getLogger(self.__class__.__name__)
        self._mongo_db_service = mongo_db_service
        self._channel_client_factory = channel_client_factory
        self._regular_user_type = bot_config["regular"]["user_type"]
        self._expert_user_type = bot_config["expert"]["user_type"]

    # TODO: Hash can be used or better way to get user by phone number
    def __get_user(
        self,
        users: List[User],
        phone_number_id,

    ) -> User:
        return next((user for user in users if user.phone_number_id == phone_number_id), None)
    
    def __get_bot_message(
        self,
        messages: List[ByoebMessageContext],
        reply_id
    ) -> ByoebMessageContext:
        return next(
            (
                message for message in messages
                if reply_id is not None
                and message.message_context.message_id == reply_id
            ),
            None
        )

    async def __create_conversations(
        self,
        messages: List[ByoebMessageContext]
    ) -> List[ByoebMessageContext]:
        phone_numbers = list(set([message.user.phone_number_id for message in messages]))
        user_ids = list(set([hashlib.md5(number.encode()).hexdigest() for number in phone_numbers]))
        byoeb_users = await self._mongo_db_service.get_users(user_ids)
        bot_message_ids = list(
            set(message.reply_context.reply_id for message in messages if message.reply_context.reply_id is not None)
        )
        bot_messages = await self._mongo_db_service.get_bot_messages(bot_message_ids)
        conversations = []
        for message in messages:
            user = self.__get_user(byoeb_users,message.user.phone_number_id)
            bot_message = self.__get_bot_message(bot_messages, message.reply_context.reply_id)
            conversation = ByoebMessageContext.model_validate(message)
            if user.user_type == self._regular_user_type:
                conversation.message_category = MessageCategory.USER_TO_BOT.value
            elif user.user_type == self._expert_user_type:
                conversation.message_category = MessageCategory.EXPERT_TO_BOT.value
            conversation.user = user
            if bot_message is None:
                conversations.append(conversation)
                continue
            conversation.reply_context.message_category = bot_message.message_category
            conversation.reply_context.reply_id = bot_message.message_context.message_id
            conversation.reply_context.reply_type = bot_message.message_context.message_type
            conversation.reply_context.reply_source_text = bot_message.message_context.message_source_text
            conversation.reply_context.reply_english_text = bot_message.message_context.message_english_text
            conversation.reply_context.additional_info = bot_message.message_context.additional_info
            conversation.cross_conversation_id = bot_message.cross_conversation_id
            conversation.cross_conversation_context = bot_message.cross_conversation_context
            conversations.append(conversation)
        return conversations
        
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
        for queries in results:
            await self._mongo_db_service.execute_message_queries(queries)

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
        from byoeb.app.configuration.dependency_setup import byoeb_expert_process
        print("Process expert message ", json.dumps(byoeb_message.model_dump()))
        self._logger.info(f"Process expert message: {byoeb_message}")
        return await byoeb_expert_process.handle([byoeb_message])