from datetime import datetime
import json
import asyncio
import byoeb_integrations.channel.whatsapp.request_payload as wa_req_payload
from typing import List, Dict, Any
from byoeb.app.configuration.config import app_config
from byoeb_core.models.byoeb.message_context import (
    ByoebMessageContext,
    MessageContext,
    ReplyContext,
    MediaContext,
)
from byoeb.services.chat.message_handlers.base import Handler
from byoeb_integrations.channel.whatsapp.meta.async_whatsapp_client import AsyncWhatsAppClient
from byoeb_core.models.whatsapp.response.message_response import WhatsAppResponse
from byoeb.app.configuration.dependency_setup import channel_client_factory

class ByoebUserSendResponse(Handler):

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
    def __prepare_whatsapp_reaction_requests(
        self,
        reaction,
        responses: List[WhatsAppResponse]
    ):
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
    
    def __prepare_whatsapp_requests(
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
    
    async def __send_whatsapp_requests(
        self,
        client: AsyncWhatsAppClient,
        payload: List[Dict[str, Any]]
    ) -> List[WhatsAppResponse]:
        tasks = []
        for request in payload:
            message_type = request["type"]
            tasks.append(client.asend_batch_messages([request], message_type))
        results = await asyncio.gather(*tasks)
        responses = [response for result in results for response in result]
        return responses

    async def __handle_expert_whatsapp(
        self,
        expert_message_context: ByoebMessageContext
    ):
        channel_client = channel_client_factory.get(expert_message_context.channel_type)  
        wa_expert_requests = self.__prepare_whatsapp_requests(expert_message_context)
        interactive_button_message = wa_expert_requests[0]
        template_verification_message = wa_expert_requests[1]
        responses = await self.__send_whatsapp_requests(channel_client, [interactive_button_message])
        # print(responses[0].response_status.status)
        if int(responses[0].response_status.status) != 200:
            responses = await self.__send_whatsapp_requests(channel_client, [template_verification_message])
        pending = app_config["channel"]["reaction"]["expert"]["pending"]
        reaction_requests = self.__prepare_whatsapp_reaction_requests(
            pending,
            responses
        )
        await self.__send_whatsapp_requests(channel_client, reaction_requests)
        return responses

    async def __handle_user_whatsapp(
        self,
        user_message_context: ByoebMessageContext
    ):
        channel_client = channel_client_factory.get(user_message_context.channel_type)
        wa_user_requests = self.__prepare_whatsapp_requests(user_message_context)
        responses = await self.__send_whatsapp_requests(channel_client, wa_user_requests)
        pending = app_config["channel"]["reaction"]["user"]["pending"]
        reaction_requests = self.__prepare_whatsapp_reaction_requests(
            pending,
            responses
        )
        await self.__send_whatsapp_requests(channel_client, reaction_requests)
        return responses
    
    def __create_bot_to_user_db_entries(
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
    
    def __create_bot_to_expert_db_entries(
        self,
        byoeb_user_message: ByoebMessageContext,
        byoeb_expert_message: ByoebMessageContext,
        user_responses: List[WhatsAppResponse],
        expert_responses: List[WhatsAppResponse]
    ):
        user_messages_context = []
        for user_response in user_responses:
            user_message_context = MessageContext(
                message_id=user_response.messages[0].id,
                message_type=byoeb_user_message.message_context.message_type,
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
                ),
                cross_conversation_context=cross_conversation_context,
                incoming_timestamp=byoeb_expert_message.incoming_timestamp,
                outgoing_timestamp=str(int(datetime.now().timestamp()))
            )
            bot_to_expert_messages.append(byoeb_message)
            
        return bot_to_expert_messages
            
    async def handle(
        self,
        messages: List[ByoebMessageContext]
    ) -> List[ByoebMessageContext]:
        byoeb_user_message = messages[0]
        byoeb_expert_message = messages[1]
        user_task = self.__handle_user_whatsapp(byoeb_user_message)
        expert_task = self.__handle_expert_whatsapp(byoeb_expert_message)
        user_responses, expert_responses = await asyncio.gather(user_task, expert_task)
        bot_to_user_db_entries = self.__create_bot_to_user_db_entries(
            byoeb_user_message,
            user_responses
        )
        bot_to_expert_db_entries = self.__create_bot_to_expert_db_entries(
            byoeb_user_message,
            byoeb_expert_message,
            user_responses,
            expert_responses
        )

        return bot_to_user_db_entries + bot_to_expert_db_entries

class ByoebExpertSendResponse(Handler):
        
    async def handle(
        self,
        messages: List[ByoebMessageContext]
    ):
        message = messages[0]
        message_english = message.message_context.message_english_text
        # convert to target channel message