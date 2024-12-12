import hashlib
import json
from typing import List
from byoeb.app.configuration.config import bot_config
from byoeb_core.models.byoeb.message_context import (
    ByoebMessageContext,
    MessageContext,
    ReplyContext,
    MediaContext,
    MessageTypes
)
from byoeb_core.models.byoeb.user import User
from byoeb.services.chat.message_handlers.base import Handler

class ByoebUserGenerateResponse(Handler):

    async def __aretrieve_chunks_list(
        self,
        text,
        k
    ) -> List[str]:
        from byoeb.app.configuration.dependency_setup import vector_store
        retrieved_chunks = await vector_store.aretrieve_top_k_chunks(text, k)
        return [chunk.text for chunk in retrieved_chunks]

    def __get_user_prompt(
        self,
        chunks,
        question
    ):
        template_user_prompt = bot_config["llm_response"]["answer_prompts"]["user_prompt"]

        # Replace placeholders with actual values
        user_prompt = template_user_prompt.replace("<CHUNKS>", chunks).replace("<QUESTION>", question)

        return user_prompt
        
    def __augment(
        self,
        user_prompt
    ):
        system_prompt = bot_config["llm_response"]["answer_prompts"]["system_prompt"]
        augmented_prompts = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        return augmented_prompts
    
    def __get_expert_additional_info(
        self,
        texts: List[str]
    ):
        additiona_info = {
            "button_titles": ["Yes", "No"],
            "template_name": bot_config["channel_templates"]["expert"]["verification"],
            "template_language": "en",  
            "template_parameters": texts
        }
        return additiona_info
    
    async def __get_new_user_message(
        self,
        message: ByoebMessageContext,
        response_text: str
    ) -> ByoebMessageContext:
        from byoeb.app.configuration.dependency_setup import text_translator
        from byoeb.app.configuration.dependency_setup import speech_translator
        additional_info = None
        user_language = message.user.user_language
        message_source_text = await text_translator.atranslate_text(
            input_text=response_text,
            source_language="en",
            target_language=user_language
        )
            
        translated_audio_message = await speech_translator.atext_to_speech(
            input_text=message_source_text,
            source_language=user_language,
        )
        additional_info = {
            "data": translated_audio_message,
            "mime_type": "audio/wav"
        }
        new_user_message = ByoebMessageContext(
            channel_type=message.channel_type,
            message_category="Bot_to_user_response",
            user=User(
                user_id=message.user.user_id,
                user_language=user_language,
                phone_number_id=message.user.phone_number_id
            ),
            message_context=MessageContext(
                message_type=MessageTypes.REGULAR_TEXT.value + '_' + MessageTypes.REGULAR_AUDIO.value,
                message_source_text=message_source_text,
                message_english_text=response_text,
                additional_info=additional_info
            ),
            reply_context=ReplyContext(
                reply_id=message.message_context.message_id,
                reply_type=message.message_context.message_type,
                media_info=message.message_context.media_info
            ),
            incoming_timestamp=message.incoming_timestamp,
        )
        
        return new_user_message
    
    def __get_new_expert_verification_message(
        self,
        message: ByoebMessageContext,
        response_text: str
    ) -> ByoebMessageContext:
        
        expert_phone_number_id = message.user.experts[0]
        expert_user_id = hashlib.md5(expert_phone_number_id.encode()).hexdigest()
        verification_question_template = bot_config["template_messages"]["expert"]["verification"]["Question"]
        verification_bot_answer_template = bot_config["template_messages"]["expert"]["verification"]["Bot_Answer"]
        verification_question = verification_question_template.replace(
            "<QUESTION>",
            message.message_context.message_english_text
        )
        verification_bot_answer = verification_bot_answer_template.replace(
            "<ANSWER>",
            response_text
        )
        verification_footer_message = bot_config["template_messages"]["expert"]["verification"]["footer"]
        additional_info = self.__get_expert_additional_info([verification_question, verification_bot_answer])
        expert_message = verification_question + "\n" + verification_bot_answer + "\n" + verification_footer_message
        new_expert_verification_message = ByoebMessageContext(
            channel_type=message.channel_type,
            message_category="Bot_to_expert_verification",
            user=User(
                user_id=expert_user_id,
                user_language='en',
                phone_number_id=expert_phone_number_id
            ),
            message_context=MessageContext(
                message_type=MessageTypes.REGULAR_TEXT.value,
                message_source_text=expert_message,
                message_english_text=expert_message,
                additional_info=additional_info
            ),
            incoming_timestamp=message.incoming_timestamp,
        )
        return new_expert_verification_message
    
    async def handle(
        self,
        messages: List[ByoebMessageContext]
    ) -> List[ByoebMessageContext]:
        message = messages[0]
        from byoeb.app.configuration.dependency_setup import llm_client
        message_english = message.message_context.message_english_text
        chunks_list = await self.__aretrieve_chunks_list(message_english, k=3)
        user_prompt = self.__get_user_prompt(", ".join(chunks_list), message_english)
        augmented_prompts = self.__augment(user_prompt)
        llm_response, response_text = await llm_client.agenerate_response(augmented_prompts)
        byoeb_user_message = await self.__get_new_user_message(message, response_text)
        if byoeb_user_message.message_context.additional_info is None:
            print("No additional info")
        print("Additional info")
        byoeb_expert_message = self.__get_new_expert_verification_message(message, response_text)
        
        if self._successor:
            return await self._successor.handle([byoeb_user_message, byoeb_expert_message])


class ByoebExpertGenerateResponse(Handler):

    def __get_user_prompt(
        self,
        question,
        answer,
        correction_text
    ):
        template_user_prompt = bot_config["llm_response"]["correction_prompts"]["user_prompt"]

        # Replace placeholders with actual values
        user_prompt = template_user_prompt.replace("<QUESTION>", question).replace("<ANSWER>", answer).replace("<CORRECTION>", correction_text)

        return user_prompt
        
    def __augment(
        self,
        user_prompt
    ):
        system_prompt = bot_config["llm_response"]["correction_prompts"]["system_prompt"]
        augmented_prompts = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        return augmented_prompts

    async def handle(
        self,
        messages: List[ByoebMessageContext]
    ):
        message = messages[0]
        from byoeb.app.configuration.dependency_setup import llm_client
        message_english = message.message_context.message_english_text
        user_prompt = self.__get_user_prompt("question", "answer", "correction_text")
        augmented_prompts = self.__augment(user_prompt)
        llm_response, response_text = await llm_client.agenerate_response(augmented_prompts)
