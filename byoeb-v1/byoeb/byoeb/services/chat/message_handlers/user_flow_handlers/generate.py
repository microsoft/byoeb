import hashlib
import byoeb.services.chat.constants as constants
from typing import List, Dict, Any
from byoeb.chat_app.configuration.config import bot_config, app_config
from byoeb.models.message_category import MessageCategory
from byoeb_core.models.byoeb.message_context import (
    ByoebMessageContext,
    MessageContext,
    ReplyContext,
    MessageTypes
)
from byoeb_core.models.byoeb.user import User
from byoeb.services.chat.message_handlers.base import Handler

class ByoebUserGenerateResponse(Handler):
    EXPERT_PENDING_EMOJI = app_config["channel"]["reaction"]["expert"]["pending"]
    USER_PENDING_EMOJI = app_config["channel"]["reaction"]["user"]["pending"]
    _expert_user_types = bot_config["expert"]
    _regular_user_type = bot_config["regular"]["user_type"]

    async def __aretrieve_chunks_list(
        self,
        text,
        k
    ) -> List[str]:
        from byoeb.chat_app.configuration.dependency_setup import vector_store
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
        texts: List[str],
        emoji = None,
        status = None
    ):
        additional_info = {
            constants.EMOJI: emoji,
            constants.VERIFICATION_STATUS: status,
            "button_titles": bot_config["template_messages"]["expert"]["verification"]["button_titles"],
            "template_name": bot_config["channel_templates"]["expert"]["verification"],
            "template_language": "en",  
            "template_parameters": texts
        }
        return additional_info
    
    def __get_expert_number_and_type(
        self,
        experts: Dict[str, List[Any]],
        query_type = "medical"
    ):
        expert_type = self._expert_user_types.get(query_type)
        if experts is None:
            return None
        if expert_type not in experts:
            return None
        return experts[expert_type][0], expert_type
    
    def __get_read_reciept_message(
        self,
        message: ByoebMessageContext,
    ) -> ByoebMessageContext:
        read_reciept_message = ByoebMessageContext(
            channel_type=message.channel_type,
            message_category=MessageCategory.READ_RECEIPT.value,
            message_context=MessageContext(
                message_id=message.message_context.message_id,
            )
        )
        return read_reciept_message
    
    async def __create_user_message(
        self,
        message: ByoebMessageContext,
        response_text: str,
        related_questions: List[str] = None,
        emoji = None,
        status = None,
    ) -> ByoebMessageContext:
        from byoeb.chat_app.configuration.dependency_setup import text_translator
        from byoeb.chat_app.configuration.dependency_setup import speech_translator
        user_language = message.user.user_language
        status_info = {
            constants.EMOJI: emoji,
            constants.VERIFICATION_STATUS: status,
        }
        message_source_text = await text_translator.atranslate_text(
            input_text=response_text,
            source_language="en",
            target_language=user_language
        )
        interactive_list_additional_info = {}
        user_message = None
        if related_questions is not None:
            interactive_list_additional_info = {
                constants.DESCRIPTION: "xyz",
                constants.ROW_TEXTS: related_questions
            }
            user_message = ByoebMessageContext(
                channel_type=message.channel_type,
                message_category=MessageCategory.BOT_TO_USER_RESPONSE.value,
                user=User(
                    user_id=message.user.user_id,
                    user_language=user_language,
                    user_type=self._regular_user_type,
                    phone_number_id=message.user.phone_number_id,
                    last_conversations=message.user.last_conversations
                ),
                message_context=MessageContext(
                    message_type=MessageTypes.INTERACTIVE_LIST.value,
                    message_source_text=message_source_text,
                    message_english_text=response_text,
                    additional_info={
                        **status_info,
                        **interactive_list_additional_info
                    }
                ),
                reply_context=ReplyContext(
                    reply_id=message.message_context.message_id,
                    reply_type=message.message_context.message_type,
                    reply_english_text=message.message_context.message_english_text,
                    reply_source_text=message.message_context.message_source_text,
                    media_info=message.message_context.media_info
                ),
                incoming_timestamp=message.incoming_timestamp,
            )
        if message.message_context.message_type == MessageTypes.REGULAR_AUDIO.value:
            translated_audio_message = await speech_translator.atext_to_speech(
                input_text=message_source_text,
                source_language=user_language,
            )
            media_info = {
                constants.DATA: translated_audio_message,
                constants.MIME_TYPE: "audio/wav",
            }
            user_message = ByoebMessageContext(
                channel_type=message.channel_type,
                message_category=MessageCategory.BOT_TO_USER_RESPONSE.value,
                user=User(
                    user_id=message.user.user_id,
                    user_language=user_language,
                    phone_number_id=message.user.phone_number_id,
                    last_conversations=message.user.last_conversations
                ),
                message_context=MessageContext(
                    message_type=MessageTypes.REGULAR_AUDIO.value,
                    message_source_text=message_source_text,
                    message_english_text=response_text,
                    additional_info={
                        **status_info,
                        **media_info,
                        **interactive_list_additional_info
                    }
                ),
                reply_context=ReplyContext(
                    reply_id=message.message_context.message_id,
                    reply_type=message.message_context.message_type,
                    reply_english_text=message.message_context.message_english_text,
                    media_info=message.message_context.media_info
                ),
                incoming_timestamp=message.incoming_timestamp,
            )
        return user_message
    
    def __create_expert_verification_message(
        self,
        message: ByoebMessageContext,
        response_text: str,
        emoji = None,
        status = None,
    ) -> ByoebMessageContext:
        
        expert_phone_number_id , expert_type= self.__get_expert_number_and_type(message.user.experts)
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
        additional_info = self.__get_expert_additional_info(
            [verification_question, verification_bot_answer],
            emoji,
            status
        )
        expert_message = verification_question + "\n" + verification_bot_answer + "\n" + verification_footer_message
        new_expert_verification_message = ByoebMessageContext(
            channel_type=message.channel_type,
            message_category=MessageCategory.BOT_TO_EXPERT_VERIFICATION.value,
            user=User(
                user_id=expert_user_id,
                user_type=expert_type,
                user_language='en',
                phone_number_id=expert_phone_number_id
            ),
            message_context=MessageContext(
                message_type=MessageTypes.INTERACTIVE_BUTTON.value,
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
    ) -> Dict[str, Any]:
        message = messages[0]
        read_reciept_message = self.__get_read_reciept_message(message)
        from byoeb.chat_app.configuration.dependency_setup import llm_client
        message_english = message.message_context.message_english_text
        chunks_list = await self.__aretrieve_chunks_list(message_english, k=3)
        user_prompt = self.__get_user_prompt(", ".join(chunks_list), message_english)
        augmented_prompts = self.__augment(user_prompt)
        llm_response, response_text = await llm_client.agenerate_response(augmented_prompts)
        byoeb_user_message = await self.__create_user_message(
            message=message,
            response_text=response_text,
            emoji=self.USER_PENDING_EMOJI,
            status=constants.PENDING,
            related_questions=["abc", "def"]
        )
        byoeb_expert_message = self.__create_expert_verification_message(
            message,
            response_text,
            self.EXPERT_PENDING_EMOJI,
            constants.PENDING
        )

        if self._successor:
            return await self._successor.handle(
                [byoeb_user_message, byoeb_expert_message, read_reciept_message]
            )