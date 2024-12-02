import json
from typing import List, Dict, Any
from byoeb_core.models.byoeb.message_context import ByoebMessageContext, MessageTypes
from byoeb.services.chat.message_handlers.base import Handler

class ByoebUserPrepareResponse(Handler):

    def __prepare_whatsapp_request(
        self,
        byoeb_message: ByoebMessageContext
    ) -> List[Dict[str, Any]]:
        import byoeb_integrations.channel.whatsapp.request_payload as wa_req_payload
        wa_text_message = wa_req_payload.get_whatsapp_text_request_from_byoeb_message(byoeb_message)
        if byoeb_message.message_context.message_type == MessageTypes.REGULAR_AUDIO.value:
            wa_audio_message = wa_req_payload.get_whatsapp_audio_request_from_byoeb_message(byoeb_message)
            return [wa_text_message, wa_audio_message]
        return [wa_text_message]
    
    async def __send_whatsapp_request(
        self,
        payload: List[Dict[str, Any]]
    ):
        pass
    
    async def handle(
        self,
        messages: List[ByoebMessageContext]
    ):
        from byoeb.app.configuration.dependency_setup import channel_client_factory
        byoeb_user_message = messages[0]
        byoeb_expert_message = messages[1]
        if byoeb_user_message.channel_type == "whatsapp":
            self.__prepare_whatsapp_request(byoeb_user_message)
        print("byoeb user message", json.dumps(byoeb_user_message.model_dump()))
        print("byoeb expert message", json.dumps(byoeb_expert_message.model_dump()))

class ByoebExpertPrepareResponse(Handler):
        
    async def handle(
        self,
        messages: List[ByoebMessageContext]
    ):
        message = messages[0]
        message_english = message.message_context.message_english_text
        # convert to target channel message