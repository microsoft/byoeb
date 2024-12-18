from datetime import datetime
import json
import asyncio
from typing import List, Dict, Any
from byoeb.app.configuration.config import app_config, bot_config
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
        pending_emoji = expert_message_context.message_context.additional_info.get("emoji")
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
        pending_emoji = user_message_context.message_context.additional_info.get("emoji")
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
        verification_status = "verification_status"
        byoeb_user_message = messages[0]
        byoeb_expert_message = messages[1]
        if byoeb_user_message.channel_type != byoeb_expert_message.channel_type:
            raise Exception("Channel type mismatch")
        channel_service = self.get_channel_service(byoeb_user_message.channel_type)
        user_task = self.__handle_user(channel_service, byoeb_user_message)
        expert_task = self.__handle_expert(channel_service, byoeb_expert_message)
        user_responses, expert_responses = await asyncio.gather(user_task, expert_task)

        byoeb_user_verification_status = byoeb_expert_message.message_context.additional_info.get(verification_status)
        byoeb_user_message.message_context.additional_info = {
            verification_status: byoeb_user_verification_status
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
            "create": self._mongo_db_service.message_create_queries(bot_to_user_convs + bot_to_expert_cross_convs)
        }
        return db_queries

class ByoebExpertSendResponse(Handler):
    _regular_user_type = bot_config["regular"]["user_type"]
    _expert_user_type = bot_config["expert"]["user_type"]

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
            if byoeb_message.user.user_type == self._expert_user_type
        ]
        return expert_messages

    def __get_user_byoeb_messages(
        self,
        byoeb_messages: List[ByoebMessageContext]
    ):
        user_messages = [
            byoeb_message for byoeb_message in byoeb_messages 
            if byoeb_message.user.user_type == self._regular_user_type
        ]

        return user_messages

    async def __handle_user(
        self,
        channel_service: BaseChannelService,
        user_message_context: List[ByoebMessageContext]
    ):
        message_reactions = [
            MessageReaction(
                reaction=user_message.reply_context.additional_info.get("emoji"),
                message_id=user_message.reply_context.reply_id,
                phone_number_id=user_message.user.phone_number_id
            )
            for user_message in user_message_context
            if user_message.reply_context and user_message.reply_context.additional_info.get("emoji") is not None
        ]
        if message_reactions:  # Proceed only if there are valid reactions
            reaction_requests = channel_service.prepare_reaction_requests(message_reactions)
            await channel_service.send_requests(reaction_requests)
        user_requests = []
        for user_message in user_message_context:
            requests = channel_service.prepare_requests(user_message)
            user_requests.extend(requests)
        responses, message_ids = await channel_service.send_requests(user_requests)

        emoji = user_message_context[0].message_context.additional_info.get("emoji")
        if emoji is None:
            return
        message_reactions = [
            MessageReaction(
                reaction=emoji,
                message_id=message_id,
                phone_number_id=user_message_context[0].user.phone_number_id
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
            and expert_message_context.reply_context.additional_info.get("emoji")
        ):
            expert_reaction = MessageReaction(
                reaction=expert_message_context.reply_context.additional_info.get("emoji"),
                message_id=expert_message_context.reply_context.reply_id,
                phone_number_id=expert_message_context.user.phone_number_id
            )
            expert_reaction_requests = channel_service.prepare_reaction_requests([expert_reaction])
            await channel_service.send_requests(expert_reaction_requests)

        return responses
        
    async def handle(
        self,
        messages: List[ByoebMessageContext]
    ):
        db_queries = {}
        byoeb_user_messages = self.__get_user_byoeb_messages(messages)
        byoeb_expert_messages = self.__get_expert_byoeb_messages(messages)
        byoeb_expert_message = byoeb_expert_messages[0]
        channel_service = self.get_channel_service(byoeb_expert_message.channel_type)
        expert_responses = await self.__handle_expert(channel_service, byoeb_expert_message)
        if len(byoeb_user_messages) == 0:
            return
        user_responses = await self.__handle_user(channel_service, byoeb_user_messages)
        update_queries = self._mongo_db_service.verification_status_update_query(
            byoeb_user_messages, 
            byoeb_expert_message
        )
        db_queries = {
            "update": update_queries
        }
        return db_queries
