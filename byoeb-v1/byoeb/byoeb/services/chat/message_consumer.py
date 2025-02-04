import logging
import asyncio
import json
import hashlib
import byoeb.utils.utils as b_utils
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from byoeb.models.message_category import MessageCategory
from byoeb.factory import ChannelClientFactory
from byoeb.chat_app.configuration.config import bot_config
from byoeb_core.models.byoeb.user import User
from byoeb.services.databases.mongo_db import UserMongoDBService, MessageMongoDBService
from byoeb_core.models.byoeb.message_context import ByoebMessageContext

class Conversation(BaseModel):
    user_message: Optional[ByoebMessageContext]
    bot_message: Optional[ByoebMessageContext]
    user: User

class MessageConsmerService:

    __timeout_seconds = 60
    def __init__(
        self,
        config,
        user_db_service: UserMongoDBService,
        message_db_service: MessageMongoDBService,
        channel_client_factory: ChannelClientFactory
    ):
        self._config = config
        self._logger = logging.getLogger(self.__class__.__name__)
        self._user_db_service = user_db_service
        self._message_db_service = message_db_service
        self._channel_client_factory = channel_client_factory
        self._regular_user_type = bot_config["regular"]["user_type"]
        self._expert_user_types = bot_config["expert"]

    # TODO: Hash can be used or better way to get user by phone number
    def __get_user(
        self,
        users: List[User],
        phone_number_id,

    ) -> User:
        return next((user for user in users if user.phone_number_id == phone_number_id), None)
    
    def __is_expert_user_type(
        self,
        user_type: str
    ):
        if user_type in self._expert_user_types.values():
            return True
        return False
            
    
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
        byoeb_users = await self._user_db_service.get_users(user_ids)
        bot_message_ids = list(
            set(message.reply_context.reply_id for message in messages if message.reply_context.reply_id is not None)
        )
        bot_messages = await self._message_db_service.get_bot_messages(bot_message_ids)
        conversations = []
        for message in messages:
            user = self.__get_user(byoeb_users,message.user.phone_number_id)
            bot_message = self.__get_bot_message(bot_messages, message.reply_context.reply_id)
            conversation = ByoebMessageContext.model_validate(message)
            if user.user_type == self._regular_user_type:
                conversation.message_category = MessageCategory.USER_TO_BOT.value
            elif self.__is_expert_user_type(user.user_type):
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
    ) -> List[ByoebMessageContext]:
        byoeb_messages = []
        successfully_processed_messages = []
        for message in messages:
            json_message = json.loads(message)
            byoeb_message = ByoebMessageContext.model_validate(json_message)
            byoeb_messages.append(byoeb_message)
        start_time = datetime.now().timestamp()
        conversations = await self.__create_conversations(byoeb_messages)
        end_time = datetime.now().timestamp()
        b_utils.log_to_text_file(f"Conversations created in: {end_time - start_time} seconds")
        task = []
        for conversation in conversations:
            conversation.user.activity_timestamp = str(int(datetime.now().timestamp()))
            # b_utils.log_to_text_file("Processing message: " + json.dumps(conversation.model_dump()))
            if conversation.user.user_type == self._regular_user_type:
                task.append(self.__process_byoebuser_conversation(conversation))
            elif self.__is_expert_user_type(conversation.user.user_type):
                task.append(self.__process_byoebexpert_conversation(conversation))
        results = await asyncio.gather(*task)
        for queries, processed_message, err in results:
            if err is not None or queries is None:
                continue
            successfully_processed_messages.append(processed_message)
        start_time = datetime.now().timestamp()
        user_queries = self._user_db_service.aggregate_queries(results)
        message_queries = self._message_db_service.aggregate_queries(results)
        await asyncio.gather(
            self._user_db_service.execute_queries(user_queries),
            self._message_db_service.execute_queries(message_queries)
        )
        end_time = datetime.now().timestamp()
        b_utils.log_to_text_file(f"DB queries executed in: {end_time - start_time} seconds")
        return successfully_processed_messages

    async def __process_byoebuser_conversation(self, byoeb_message):
        from byoeb.chat_app.configuration.dependency_setup import byoeb_user_process
        byoeb_message_copy = byoeb_message.model_copy(deep=True)
        try:
            queries = await asyncio.wait_for(byoeb_user_process.handle([byoeb_message]), timeout=self.__timeout_seconds)
            return queries, byoeb_message_copy, None
        except asyncio.TimeoutError:
            error_message = f"Timeout error: Task took longer than {self.__timeout_seconds} seconds."
            self._logger.error(error_message)
            print(error_message)
            return None, byoeb_message_copy, "TimeoutError"
        except Exception as e:
            self._logger.error(f"Error processing user message: {e}")
            print("Error processing user message: ", e)
            return None, byoeb_message_copy, e

    async def __process_byoebexpert_conversation(
        self,
        byoeb_message: ByoebMessageContext
    ):
        from byoeb.chat_app.configuration.dependency_setup import byoeb_expert_process
        # print("Process expert message ", json.dumps(byoeb_message.model_dump()))
        byoeb_message_copy = byoeb_message.model_copy(deep=True)
        self._logger.info(f"Process expert message: {byoeb_message}")
        try:
            queries = await asyncio.wait_for(byoeb_expert_process.handle([byoeb_message]), timeout=self.__timeout_seconds)
            return queries, byoeb_message_copy, None
        except asyncio.TimeoutError:
            error_message = f"Timeout error: Expert process task took longer than {self.__timeout_seconds} seconds."
            self._logger.error(error_message)
            print(error_message)
            return None, byoeb_message_copy, "TimeoutError"
        except Exception as e:
            self._logger.error(f"Error processing expert message: {e}")
            print("Error processing expert message: ", e)
            return None, byoeb_message_copy, e