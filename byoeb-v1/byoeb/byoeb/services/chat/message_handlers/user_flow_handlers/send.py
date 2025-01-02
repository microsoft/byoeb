import asyncio
import byoeb.services.chat.constants as constants
from byoeb.chat_app.configuration.config import app_config, bot_config
from byoeb.services.chat import utils
from typing import Any, Dict, List
from byoeb.models.message_category import MessageCategory
from byoeb_core.models.byoeb.message_context import ByoebMessageContext, MessageTypes
from byoeb.services.channel.base import BaseChannelService, MessageReaction
from byoeb.services.databases.mongo_db import MongoDBService
from byoeb.services.chat.message_handlers.base import Handler
from byoeb.services.channel.base import MessageReaction

class ByoebUserSendResponse(Handler):
    __max_last_active_duration_seconds: int = app_config["app"]["max_last_active_duration_seconds"]
    _regular_user_type = bot_config["regular"]["user_type"]
    _expert_user_types = bot_config["expert"]

    def __init__(
        self,
        mongo_db_service: MongoDBService,
    ):
        self._mongo_db_service = mongo_db_service

    def get_channel_service(
        self,
        channel_type
    ) -> BaseChannelService:
        if channel_type == "whatsapp":
            from byoeb.services.channel.whatsapp import WhatsAppService
            return WhatsAppService()
        return None
    
    def __get_expert_byoeb_messages(
        self,
        byoeb_messages: List[ByoebMessageContext]
    ):
        expert_messages = [
            byoeb_message for byoeb_message in byoeb_messages 
            if byoeb_message.user is not None and byoeb_message.user.user_type in self._expert_user_types.values()
        ]
        return expert_messages

    def __get_user_byoeb_messages(
        self,
        byoeb_messages: List[ByoebMessageContext]
    ):
        user_messages = [
            byoeb_message for byoeb_message in byoeb_messages 
            if byoeb_message.user is not None and byoeb_message.user.user_type == self._regular_user_type
        ]
        return user_messages
    
    def __get_read_receipt_byoeb_messages(
        self,
        byoeb_messages: List[ByoebMessageContext]
    ):
        read_receipt_messages = [
            byoeb_message for byoeb_message in byoeb_messages
            if byoeb_message.message_category == MessageCategory.READ_RECEIPT.value
        ]
        return read_receipt_messages
    
    def __prepare_db_queries(
        self,
        convs: List[ByoebMessageContext],
        byoeb_user_message: ByoebMessageContext,
    ):
        message_db_queries = {
            constants.CREATE: self._mongo_db_service.message_create_queries(convs)
        }
        qa = {
            constants.QUESTION: byoeb_user_message.reply_context.reply_english_text,
            constants.ANSWER: byoeb_user_message.message_context.message_english_text
        }
        user_db_queries = {
            constants.UPDATE: [self._mongo_db_service.user_activity_update_query(byoeb_user_message.user, qa)]
        }
        return {
            constants.MESSAGE_DB_QUERIES: message_db_queries,
            constants.USER_DB_QUERIES: user_db_queries
        }
        

    async def __handle_expert(
        self,
        channel_service: BaseChannelService,
        expert_message_context: ByoebMessageContext
    ):
        user_timestamp = await self._mongo_db_service.get_user_activity_timestamp(expert_message_context.user.user_id)
        last_active_duration_seconds = utils.get_last_active_duration_seconds(user_timestamp)
        expert_requests = channel_service.prepare_requests(expert_message_context)
        interactive_button_message = expert_requests[0]
        template_verification_message = expert_requests[1]
        
        if last_active_duration_seconds >= self.__max_last_active_duration_seconds:
            expert_message_context.message_context.message_type = MessageTypes.TEMPLATE_BUTTON.value
            responses, message_ids = await channel_service.send_requests([template_verification_message])
        else:
            responses, message_ids = await channel_service.send_requests([interactive_button_message])
        pending_emoji = expert_message_context.message_context.additional_info.get(constants.EMOJI)
        message_reactions = [
            MessageReaction(
                reaction=pending_emoji,
                message_id=message_id,
                phone_number_id=expert_message_context.user.phone_number_id
            )
            for message_id in message_ids if message_id is not None
        ]

        reaction_requests = channel_service.prepare_reaction_requests(message_reactions)
        await channel_service.send_requests(reaction_requests)
        return responses

    async def __handle_user(
        self,
        channel_service: BaseChannelService,
        user_message_context: ByoebMessageContext
    ):
        responses = []
        message_ids = []
        user_requests = channel_service.prepare_requests(user_message_context)
        if user_message_context.message_context.message_type == MessageTypes.REGULAR_AUDIO.value:
            user_message_copy = user_message_context.__deepcopy__()
            user_message_copy.reply_context = None
            user_requests_no_tag = channel_service.prepare_requests(user_message_copy)
            audio_tag_message = user_requests[1]
            text_no_tag_message = user_requests_no_tag[0]
            response_audio, message_id_audio = await channel_service.send_requests([audio_tag_message])
            response_text, message_id_text = await channel_service.send_requests([text_no_tag_message])
            responses = response_audio + response_text
            message_ids = message_id_audio + message_id_text
        else:
            responses, message_ids = await channel_service.send_requests(user_requests)
        pending_emoji = user_message_context.message_context.additional_info.get(constants.EMOJI)
        message_reactions = [
            MessageReaction(
                reaction=pending_emoji,
                message_id=message_id,
                phone_number_id=user_message_context.user.phone_number_id
            )
            for message_id in message_ids if message_id is not None
        ]
        reaction_requests = channel_service.prepare_reaction_requests(message_reactions)
        await channel_service.send_requests(reaction_requests)
        return responses

    async def handle(
        self,
        messages: List[ByoebMessageContext]
    ) -> Dict[str, Any]:
        db_queries = {}
        verification_status = constants.VERIFICATION_STATUS
        read_receipt_messages = self.__get_read_receipt_byoeb_messages(messages)
        byoeb_user_messages = self.__get_user_byoeb_messages(messages)
        byoeb_expert_messages = self.__get_expert_byoeb_messages(messages)
        byoeb_user_message = byoeb_user_messages[0]
        byoeb_expert_message = byoeb_expert_messages[0]
        if byoeb_user_message.channel_type != byoeb_expert_message.channel_type:
            raise Exception("Channel type mismatch")
        channel_service = self.get_channel_service(byoeb_user_message.channel_type)
        await channel_service.amark_read(read_receipt_messages)
        user_task = self.__handle_user(channel_service, byoeb_user_message)
        expert_task = self.__handle_expert(channel_service, byoeb_expert_message)
        user_responses, expert_responses = await asyncio.gather(user_task, expert_task)

        byoeb_user_verification_status = byoeb_expert_message.message_context.additional_info.get(verification_status)
        related_questions = byoeb_user_message.message_context.additional_info.get(constants.ROW_TEXTS)
        byoeb_user_message.message_context.additional_info = {
            verification_status: byoeb_user_verification_status,
            constants.RELATED_QUESTIONS: related_questions
        }
        bot_to_user_convs = channel_service.create_conv(
            byoeb_user_message,
            user_responses
        )

        byoeb_expert_verification_status = byoeb_expert_message.message_context.additional_info.get(verification_status)
        byoeb_expert_message.message_context.additional_info = {
            verification_status: byoeb_expert_verification_status
        }
        bot_to_expert_cross_convs = channel_service.create_cross_conv(
            byoeb_user_message,
            byoeb_expert_message,
            user_responses,
            expert_responses
        )
        db_queries = self.__prepare_db_queries(bot_to_user_convs + bot_to_expert_cross_convs, byoeb_user_message)
        return db_queries