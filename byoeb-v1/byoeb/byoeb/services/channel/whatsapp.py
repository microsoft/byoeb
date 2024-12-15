import asyncio
import json
import byoeb_integrations.channel.whatsapp.request_payload as wa_req_payload
from byoeb.services.channel.base import BaseChannelService
from byoeb_integrations.channel.whatsapp.meta.async_whatsapp_client import AsyncWhatsAppClient
from byoeb_core.models.byoeb.message_context import (
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
    def __has_audio_additional_info(
        self,
        byoeb_message: ByoebMessageContext
    ):
        return (
            byoeb_message.message_context.additional_info is not None and
            "data" in byoeb_message.message_context.additional_info and
            "mime_type" in byoeb_message.message_context.additional_info and
            "audio" in byoeb_message.message_context.additional_info.get("mime_type")
        )
    
    def __has_interactive_list_additional_info(
        self,
        byoeb_message: ByoebMessageContext
    ):
        return (
            byoeb_message.message_context.additional_info is not None and
            "row_texts" in byoeb_message.message_context.additional_info
        )
    
    def __has_interactive_button_additional_info(
        self,
        byoeb_message: ByoebMessageContext
    ):
        return (
            byoeb_message.message_context.additional_info is not None and
            "button_titles" in byoeb_message.message_context.additional_info
        )
    
    def __has_template_additional_info(    
        self,
        byoeb_message: ByoebMessageContext
    ):
        return (    
            byoeb_message.message_context.additional_info is not None and
            "template_name" in byoeb_message.message_context.additional_info and
            "template_language" in byoeb_message.message_context.additional_info and
            "template_parameters" in byoeb_message.message_context.additional_info
        )
    def prepare_reaction_requests(
        self,
        reaction,
        responses: List[WhatsAppResponse]
    ) -> List[Dict[str, Any]]:
        reactions = []
        for response in responses:
            message_id = response.messages[0].id
            phone_number_id = response.contacts[0].wa_id
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
        if self.__has_interactive_button_additional_info(byoeb_message):
            wa_interactive_button_message = wa_req_payload.get_whatsapp_interactive_button_request_from_byoeb_message(byoeb_message)
            wa_requests.append(wa_interactive_button_message)
        elif self.__has_interactive_list_additional_info(byoeb_message):  
            wa_interactive_list_message = wa_req_payload.get_whatsapp_interactive_list_request_from_byoeb_message(byoeb_message)
            wa_requests.append(wa_interactive_list_message)
        else:
            wa_text_message = wa_req_payload.get_whatsapp_text_request_from_byoeb_message(byoeb_message)
            wa_requests.append(wa_text_message)
        if self.__has_template_additional_info(byoeb_message):
            wa_template_message = wa_req_payload.get_whatsapp_template_request_from_byoeb_message(byoeb_message)
            print("Whatsapp template message", json.dumps(wa_template_message))
            wa_requests.append(wa_template_message)
        if self.__has_audio_additional_info(byoeb_message):
            wa_audio_message = wa_req_payload.get_whatsapp_audio_request_from_byoeb_message(byoeb_message)
            wa_requests.append(wa_audio_message)       
        return wa_requests
    
    async def send_requests(
        self,
        payload: List[Dict[str, Any]]
    ) -> List[WhatsAppResponse]:
        from byoeb.app.configuration.dependency_setup import channel_client_factory
        client = channel_client_factory.get(self.__client_type)
        tasks = []
        for request in payload:
            message_type = request["type"]
            tasks.append(client.asend_batch_messages([request], message_type))
        results = await asyncio.gather(*tasks)
        responses = [response for result in results for response in result]
        return responses
    
    def create_bot_to_user_db_entries(
        self,
        byoeb_user_message: ByoebMessageContext,
        responses: List[WhatsAppResponse]
    ) -> List[ByoebMessageContext]:
        bot_to_user_messages = []
        for response in responses:
            media_info = None
            if response.media_message is not None:
                media_info = MediaContext(
                    media_id=response.media_message.id
                )
            byoeb_message = ByoebMessageContext( 
                channel_type=byoeb_user_message.channel_type,
                message_category=byoeb_user_message.message_category,
                user=byoeb_user_message.user,
                message_context=MessageContext(
                    message_id=response.messages[0].id,
                    message_type=byoeb_user_message.message_context.message_type,
                    message_english_text=byoeb_user_message.message_context.message_english_text,
                    message_source_text=byoeb_user_message.message_context.message_source_text,
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
    
    def create_cross_conv_db_entries(
        self,
        byoeb_user_message: ByoebMessageContext,
        byoeb_expert_message: ByoebMessageContext,
        user_responses: List[WhatsAppResponse],
        expert_responses: List[WhatsAppResponse]
    ):
        user_messages_context = []
        for user_response in user_responses:
            message_type = MessageTypes.REGULAR_TEXT.value
            if user_response.media_message is not None:
                message_type = MessageTypes.REGULAR_AUDIO.value
            user_message_context = MessageContext(
                message_id=user_response.messages[0].id,
                message_type=message_type
            )
            user_messages_context.append(user_message_context)
        
        cross_conversation_context = {
            "user": byoeb_user_message.user,
            "messages_context": user_messages_context
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