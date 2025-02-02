import byoeb.services.chat.constants as constants
import byoeb.services.chat.utils as utils
from typing import List, Dict, Any
from byoeb_core.models.byoeb.message_context import ByoebMessageContext, MessageTypes
from byoeb.services.channel.base import BaseChannelService, MessageReaction
from byoeb.services.databases.mongo_db import UserMongoDBService, MessageMongoDBService
from byoeb.services.chat.message_handlers.base import Handler
from byoeb.services.channel.base import MessageReaction

class ByoebExpertSendResponse(Handler):
    def __init__(
        self,
        user_db_service: UserMongoDBService,
        message_db_service: MessageMongoDBService,
    ):
        self._user_db_service = user_db_service
        self._message_db_service = message_db_service

    def get_channel_service(
        self,
        channel_type
    ) -> BaseChannelService:
        if channel_type == "whatsapp":
            from byoeb.services.channel.whatsapp import WhatsAppService
            return WhatsAppService()
        return None
    
    def __modify_user_messages_context(
        self,
        user_messages_context: List[ByoebMessageContext]
    ):
        has_audio = False
        audio_message = None

        for user_message in user_messages_context:
            if (user_message.message_context.message_type == MessageTypes.REGULAR_AUDIO.value
                and utils.has_audio_additional_info(user_message)):
                has_audio = True
                audio_message = user_message
                break

        if not has_audio:
            return user_messages_context

        new_contexts = [audio_message] 
        for user_message in user_messages_context:
            if user_message != audio_message:
                new_context = user_message.__deepcopy__()
                new_context.reply_context = None
                new_contexts.append(new_context)

        return new_contexts
    
    def __prepare_db_queries(
        self,
        byoeb_user_messages: List[ByoebMessageContext],
        byoeb_expert_message: ByoebMessageContext,
    ):
        message_update_queries = []
        if byoeb_user_messages is None or len(byoeb_user_messages) == 0:
            message_update_queries = []
        else:
            message_update_queries = (
                self._message_db_service.correction_update_query(byoeb_user_messages, byoeb_expert_message) +
                self._message_db_service.verification_status_update_query(byoeb_user_messages, byoeb_expert_message)
            )
        user_update_queries = [self._user_db_service.user_activity_update_query(byoeb_expert_message.user)]
        return {
            constants.MESSAGE_DB_QUERIES: {
                constants.UPDATE: message_update_queries
            },
            constants.USER_DB_QUERIES: {
                constants.UPDATE: user_update_queries
            }
        }
        
    async def __handle_user(
        self,
        channel_service: BaseChannelService,
        user_messages_context: List[ByoebMessageContext]
    ):
        message_reactions = [
            MessageReaction(
                reaction=user_message.reply_context.additional_info.get(constants.EMOJI),
                message_id=user_message.reply_context.reply_id,
                phone_number_id=user_message.user.phone_number_id
            )
            for user_message in user_messages_context
            if user_message.reply_context and user_message.reply_context.additional_info.get(constants.EMOJI) is not None
        ]
        if message_reactions:  # Proceed only if there are valid reactions
            reaction_requests = channel_service.prepare_reaction_requests(message_reactions)
            await channel_service.send_requests(reaction_requests)
        responses = []
        message_ids = []
        modified_user_messages_context = self.__modify_user_messages_context(user_messages_context)
        for user_message in modified_user_messages_context:
            requests = channel_service.prepare_requests(user_message)
            response, message_id = await channel_service.send_requests(requests)
            responses.extend(response)
            message_ids.extend(message_id)

        emoji = user_messages_context[0].message_context.additional_info.get(constants.EMOJI)
        if emoji is None:
            return
        message_reactions = [
            MessageReaction(
                reaction=emoji,
                message_id=message_id,
                phone_number_id=user_messages_context[0].user.phone_number_id
            )
            for message_id in message_ids if message_id is not None
        ]
        reaction_requests = channel_service.prepare_reaction_requests(message_reactions)
        await channel_service.send_requests(reaction_requests)
        return responses

    async def __handle_expert(
        self,
        channel_service: BaseChannelService,
        expert_message_context: ByoebMessageContext
    ):
        expert_requests = channel_service.prepare_requests(expert_message_context)
        responses, _ = await channel_service.send_requests(expert_requests)

        # Check if reply_id is present
        if (expert_message_context.reply_context
            and expert_message_context.reply_context.reply_id
            and expert_message_context.reply_context.additional_info.get(constants.EMOJI)
        ):
            expert_reaction = MessageReaction(
                reaction=expert_message_context.reply_context.additional_info.get(constants.EMOJI),
                message_id=expert_message_context.reply_context.reply_id,
                phone_number_id=expert_message_context.user.phone_number_id
            )
            expert_reaction_requests = channel_service.prepare_reaction_requests([expert_reaction])
            await channel_service.send_requests(expert_reaction_requests)

        return responses
        
    async def handle(
        self,
        messages: List[ByoebMessageContext]
    ) -> Dict[str, Any]:
        db_queries = {}
        read_receipt_messages = utils.get_read_receipt_byoeb_messages(messages)
        byoeb_user_messages = utils.get_user_byoeb_messages(messages)
        byoeb_expert_messages = utils.get_expert_byoeb_messages(messages)
        byoeb_expert_message = byoeb_expert_messages[0]
        channel_service = self.get_channel_service(byoeb_expert_message.channel_type)
        await channel_service.amark_read(read_receipt_messages)
        expert_responses = await self.__handle_expert(channel_service, byoeb_expert_message)
        if byoeb_user_messages is not None and len(byoeb_user_messages) != 0:
            user_responses = await self.__handle_user(channel_service, byoeb_user_messages)
        db_queries = self.__prepare_db_queries(byoeb_user_messages, byoeb_expert_message)
        return db_queries