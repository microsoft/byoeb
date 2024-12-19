import asyncio
import byoeb.services.chat.constants as constants
from typing import List
from byoeb_core.models.byoeb.message_context import ByoebMessageContext
from byoeb.services.channel.base import BaseChannelService, MessageReaction
from byoeb.services.databases.mongo_db import MongoDBService
from byoeb.services.chat.message_handlers.base import Handler
from byoeb.services.channel.base import MessageReaction

class ByoebUserSendResponse(Handler):

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

    async def __handle_expert(
        self,
        channel_service: BaseChannelService,
        expert_message_context: ByoebMessageContext
    ):
        expert_requests = channel_service.prepare_requests(expert_message_context)
        interactive_button_message = expert_requests[0]
        template_verification_message = expert_requests[1]
        responses, message_ids = await channel_service.send_requests([interactive_button_message])
        # print(responses[0].response_status.status)
        if int(responses[0].response_status.status) != 200:
            responses = await channel_service.send_requests([template_verification_message])
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
        user_requests = channel_service.prepare_requests(user_message_context)
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
    ) -> List[ByoebMessageContext]:
        db_queries = {}
        verification_status = constants.VERIFICATION_STATUS
        byoeb_user_message = messages[0]
        byoeb_expert_message = messages[1]
        if byoeb_user_message.channel_type != byoeb_expert_message.channel_type:
            raise Exception("Channel type mismatch")
        channel_service = self.get_channel_service(byoeb_user_message.channel_type)
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
        db_queries = {
            constants.CREATE: self._mongo_db_service.message_create_queries(bot_to_user_convs + bot_to_expert_cross_convs)
        }
        return db_queries