import asyncio
import byoeb.services.chat.constants as constants
import byoeb.services.chat.utils as utils 
import byoeb_integrations.channel.whatsapp.request_payload as wa_req_payload
from byoeb.services.channel.base import BaseChannelService, MessageReaction
from byoeb_core.models.byoeb.message_context import (
    User,
    ByoebMessageContext,   
    MessageContext,
    ReplyContext,
    MediaContext,
    MessageTypes
)
from byoeb_core.models.whatsapp.response.message_response import WhatsAppResponse
from typing import List, Dict, Any, Tuple
from datetime import datetime


class WhatsAppService(BaseChannelService):
    __client_type = "whatsapp"

    def prepare_reaction_requests(
        self,
        message_reactions: List[MessageReaction]
    ) -> List[Dict[str, Any]]:
        reactions = []
        for message_reaction in message_reactions:
            message_id = message_reaction.message_id
            phone_number_id = message_reaction.phone_number_id
            reaction = message_reaction.reaction
            reaction_request = wa_req_payload.get_whatsapp_reaction_request(
                phone_number_id,
                message_id,
                reaction
            )
            reactions.append(reaction_request)
        return reactions
    
    def prepare_requests(
        self,
        byoeb_message: ByoebMessageContext
    ) -> List[Dict[str, Any]]:
        wa_requests = []
        if utils.has_interactive_button_additional_info(byoeb_message):
            wa_interactive_button_message = wa_req_payload.get_whatsapp_interactive_button_request_from_byoeb_message(byoeb_message)
            wa_requests.append(wa_interactive_button_message)
        elif utils.has_interactive_list_additional_info(byoeb_message):
            wa_interactive_list_message = wa_req_payload.get_whatsapp_interactive_list_request_from_byoeb_message(byoeb_message)
            wa_requests.append(wa_interactive_list_message)
        elif utils.has_text(byoeb_message):
            wa_text_message = wa_req_payload.get_whatsapp_text_request_from_byoeb_message(byoeb_message)
            wa_requests.append(wa_text_message)
        if utils.has_template_additional_info(byoeb_message):
            wa_template_message = wa_req_payload.get_whatsapp_template_request_from_byoeb_message(byoeb_message)
            # print("Whatsapp template message", json.dumps(wa_template_message))
            wa_requests.append(wa_template_message)
        if utils.has_audio_additional_info(byoeb_message):
            wa_audio_message = wa_req_payload.get_whatsapp_audio_request_from_byoeb_message(byoeb_message)
            wa_requests.append(wa_audio_message)
        return wa_requests
    
    async def amark_read(
        self,
        messages: List[ByoebMessageContext]
    ) -> List[WhatsAppResponse]:
        from byoeb.chat_app.configuration.dependency_setup import channel_client_factory
        client = await channel_client_factory.get(self.__client_type)
        tasks = []
        for message in messages:
            if message.message_context.message_id is None:
                continue
            tasks.append(client.amark_as_read(message.message_context.message_id))
        await asyncio.gather(*tasks)
    
    async def send_requests(
        self,
        requests: List[Dict[str, Any]]
    ) -> Tuple[List[WhatsAppResponse], List[str]]:
        from byoeb.chat_app.configuration.dependency_setup import channel_client_factory
        client = await channel_client_factory.get(self.__client_type)
        tasks = []
        for request in requests:
            message_type = request["type"]
            tasks.append(client.asend_batch_messages([request], message_type))
        results = await asyncio.gather(*tasks)
        responses = [response for result in results for response in result]
        message_ids = [response.messages[0].id if response.messages else None for response in responses]
        return responses, message_ids
    
    def create_conv(
        self,
        byoeb_user_message: ByoebMessageContext,
        responses: List[WhatsAppResponse]
    ) -> List[ByoebMessageContext]:
        bot_to_user_messages = []
        for response in responses:
            media_info = None
            message_type = None
            if response.media_message is not None:
                media_info = MediaContext(
                    media_id=response.media_message.id
                )
                message_type = MessageTypes.REGULAR_AUDIO.value
            elif byoeb_user_message.message_context.additional_info.get(constants.RELATED_QUESTIONS) is not None:
                message_type = MessageTypes.INTERACTIVE_LIST.value
            byoeb_message = ByoebMessageContext( 
                channel_type=byoeb_user_message.channel_type,
                message_category=byoeb_user_message.message_category,
                user=User(
                    user_id=byoeb_user_message.user.user_id,
                    user_type=byoeb_user_message.user.user_type,
                    user_language=byoeb_user_message.user.user_language,
                    test_user=byoeb_user_message.user.test_user,
                    phone_number_id=byoeb_user_message.user.phone_number_id,
                ),
                message_context=MessageContext(
                    message_id=response.messages[0].id,
                    message_type=message_type,
                    message_english_text=byoeb_user_message.message_context.message_english_text,
                    message_source_text=byoeb_user_message.message_context.message_source_text,
                    additional_info=byoeb_user_message.message_context.additional_info,
                    media_info=media_info
                ),
                reply_context=ReplyContext(
                    reply_id=byoeb_user_message.reply_context.reply_id,
                    reply_type=byoeb_user_message.reply_context.reply_type,
                ),
                incoming_timestamp=byoeb_user_message.incoming_timestamp,
                outgoing_timestamp=str(int(datetime.now().timestamp()))
            )
            bot_to_user_messages.append(byoeb_message)
        return bot_to_user_messages
    
    def create_cross_conv(
        self,
        byoeb_user_message: ByoebMessageContext,
        byoeb_expert_message: ByoebMessageContext,
        user_responses: List[WhatsAppResponse],
        expert_responses: List[WhatsAppResponse]
    ):
        user_messages_context = []
        for user_response in user_responses:
            message_type = MessageTypes.INTERACTIVE_LIST.value
            if user_response.media_message is not None:
                message_type = MessageTypes.REGULAR_AUDIO.value
            message_context = MessageContext(
                message_id=user_response.messages[0].id,
                message_type=message_type,
                additional_info=byoeb_user_message.message_context.additional_info
            )
            reply_context = ReplyContext(
                reply_id=byoeb_user_message.reply_context.reply_id,
            )
            user_message_context = ByoebMessageContext(
                channel_type=byoeb_user_message.channel_type,
                message_context=message_context,
                reply_context=reply_context
            )
            user_messages_context.append(user_message_context)
        
        cross_conversation_context = {
            constants.USER: User(
                    user_id=byoeb_user_message.user.user_id,
                    user_type=byoeb_user_message.user.user_type,
                    user_language=byoeb_user_message.user.user_language,
                    test_user=byoeb_user_message.user.test_user,
                    phone_number_id=byoeb_user_message.user.phone_number_id,
                ),
            constants.MESSAGES_CONTEXT: user_messages_context
        }
        bot_to_expert_messages = []
        for expert_response in expert_responses:
            byoeb_message = ByoebMessageContext( 
                channel_type=byoeb_expert_message.channel_type,
                message_category=byoeb_expert_message.message_category,
                user=byoeb_expert_message.user,
                message_context=MessageContext(
                    message_id=expert_response.messages[0].id,
                    message_type=byoeb_expert_message.message_context.message_type,
                    message_english_text=byoeb_expert_message.message_context.message_english_text,
                    message_source_text=byoeb_expert_message.message_context.message_source_text,
                    additional_info=byoeb_expert_message.message_context.additional_info
                ),
                cross_conversation_context=cross_conversation_context,
                incoming_timestamp=byoeb_expert_message.incoming_timestamp,
                outgoing_timestamp=str(int(datetime.now().timestamp()))
            )
            bot_to_expert_messages.append(byoeb_message)
            
        return bot_to_expert_messages