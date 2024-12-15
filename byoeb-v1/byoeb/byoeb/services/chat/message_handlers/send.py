from datetime import datetime
import json
import asyncio
from typing import List, Dict, Any
from byoeb.app.configuration.config import app_config
from byoeb_core.models.byoeb.message_context import ByoebMessageContext
from byoeb.services.channel.base import BaseChannelService
from byoeb.services.chat.message_handlers.base import Handler


class ByoebUserSendResponse(Handler):

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
        wa_expert_requests = channel_service.prepare_requests(expert_message_context)
        interactive_button_message = wa_expert_requests[0]
        template_verification_message = wa_expert_requests[1]
        responses = await channel_service.send_requests([interactive_button_message])
        # print(responses[0].response_status.status)
        if int(responses[0].response_status.status) != 200:
            responses = await channel_service.send_requests([template_verification_message])
        pending_emoji = expert_message_context.message_context.additional_info.get("emoji")
        reaction_requests = channel_service.prepare_reaction_requests(
            pending_emoji,
            responses
        )
        await channel_service.send_requests(reaction_requests)
        return responses

    async def __handle_user(
        self,
        channel_service: BaseChannelService,
        user_message_context: ByoebMessageContext
    ):
        wa_user_requests = channel_service.prepare_requests(user_message_context)
        responses = await channel_service.send_requests( wa_user_requests)
        pending_emoji = user_message_context.message_context.additional_info.get("emoji")
        reaction_requests = channel_service.prepare_reaction_requests(
            pending_emoji,
            responses
        )
        await channel_service.send_requests(reaction_requests)
        return responses
    
    async def handle(
        self,
        messages: List[ByoebMessageContext]
    ) -> List[ByoebMessageContext]:
        verification_status = "verification_status"
        byoeb_user_message = messages[0]
        byoeb_expert_message = messages[1]
        if byoeb_user_message.channel_type != byoeb_expert_message.channel_type:
            raise Exception("Channel type mismatch")
        channel_service = self.get_channel_service(byoeb_user_message.channel_type)
        user_task = self.__handle_user(channel_service, byoeb_user_message)
        expert_task = self.__handle_expert(channel_service, byoeb_expert_message)
        user_responses, expert_responses = await asyncio.gather(user_task, expert_task)
        bot_to_user_db_entries = channel_service.create_bot_to_user_db_entries(
            byoeb_user_message,
            user_responses
        )
        byoeb_expert_verification_status = byoeb_expert_message.message_context.additional_info.get(verification_status)
        byoeb_expert_message.message_context.additional_info = {
            verification_status: byoeb_expert_verification_status
        }
        bot_to_expert_db_entries = channel_service.create_cross_conv_db_entries(
            byoeb_user_message,
            byoeb_expert_message,
            user_responses,
            expert_responses
        )

        return bot_to_user_db_entries + bot_to_expert_db_entries

class ByoebExpertSendResponse(Handler):

    def get_channel_service(
        self,
        channel_type
    ) -> BaseChannelService:
        if channel_type == "whatsapp":
            from byoeb.services.channel.whatsapp import WhatsAppService
            return WhatsAppService()
        return None
        
    async def handle(
        self,
        messages: List[ByoebMessageContext]
    ):
        byoeb_user_message = messages[0]
        byoeb_expert_message = messages[1]
        channel_service = self.get_channel_service(byoeb_expert_message.channel_type)
        
        return
