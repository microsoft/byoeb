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
        if message.message_context.message_type == MessageTypes.REGULAR_AUDIO.value:
            
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
            user=message.user,
            message_context=MessageContext(
                message_type=message.message_context.message_type,
                message_source_text=message_source_text,
                message_english_text=response_text,
                additional_info=additional_info
            ),
            reply_context=ReplyContext(
                reply_id=message.message_context.message_id,
                reply_type=message.message_context.message_type,
                reply_source_text=message.message_context.message_source_text,
                reply_english_text=message.message_context.message_english_text,
                media_info=message.message_context.media_info
            )
        )
        
        return new_user_message
    
    def __get_new_expert_verification_message(
        self,
        user_message: ByoebMessageContext
    ) -> ByoebMessageContext:
        
        expert_phone_number_id = user_message.user.experts[0]
        expert_user_id = hashlib.md5(expert_phone_number_id.encode()).hexdigest()
        expert_message = f"""*Question*: {user_message.reply_context.reply_english_text}\n
        *Answer*: {user_message.message_context.message_english_text}
        """
        new_expert_verification_message = ByoebMessageContext(
            channel_type=user_message.channel_type,
            message_category="Bot_to_expert_verification",
            user=User(
                user_id=expert_user_id,
                phone_number_id=expert_phone_number_id
            ),
            message_context=MessageContext(
                message_source_text=expert_message,
                message_english_text=expert_message
            )
        )
        return new_expert_verification_message
    
    async def handle(
        self,
        messages: List[ByoebMessageContext]
    ):
        message = messages[0]
        from byoeb.app.configuration.dependency_setup import llm_client
        message_english = message.message_context.message_english_text
        chunks_list = await self.__aretrieve_chunks_list(message_english, k=3)
        user_prompt = self.__get_user_prompt(", ".join(chunks_list), message_english)
        augmented_prompts = self.__augment(user_prompt)
        llm_response, response_text = await llm_client.agenerate_response(augmented_prompts)
        byoeb_user_message = await self.__get_new_user_message(message, response_text)
        byoeb_expert_message = self.__get_new_expert_verification_message(byoeb_user_message)

        # populate byoeb message context with user information
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
