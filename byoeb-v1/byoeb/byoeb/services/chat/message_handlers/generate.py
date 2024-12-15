import hashlib
import json
import re
from typing import List
from byoeb.app.configuration.config import bot_config, app_config
from byoeb.models.message_category import MessageCategory
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

    VERIFICATION_STATUS = "verification_status"
    PENDING = "pending"
    EXPERT_PENDING_EMOJI = app_config["channel"]["reaction"]["expert"]["pending"]
    USER_PENDING_EMOJI = app_config["channel"]["reaction"]["user"]["pending"]

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
        texts: List[str],
        emoji = None,
        status = None
    ):
        additional_info = {
            "emoji": emoji,
            self.VERIFICATION_STATUS: status,
            "button_titles": bot_config["template_messages"]["expert"]["verification"]["button_titles"],
            "template_name": bot_config["channel_templates"]["expert"]["verification"],
            "template_language": "en",  
            "template_parameters": texts
        }
        return additional_info
    
    async def __get_new_user_message(
        self,
        message: ByoebMessageContext,
        response_text: str,
        emoji = None
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
            "emoji": emoji,
            "data": translated_audio_message,
            "mime_type": "audio/wav"
        }
        new_user_message = ByoebMessageContext(
            channel_type=message.channel_type,
            message_category=MessageCategory.BOT_TO_USER_RESPONSE.value,
            user=User(
                user_id=message.user.user_id,
                user_language=user_language,
                phone_number_id=message.user.phone_number_id
            ),
            message_context=MessageContext(
                message_type=MessageTypes.REGULAR_TEXT.value + ',' + MessageTypes.REGULAR_AUDIO.value,
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
        response_text: str,
        emoji = None,
        status = None,
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
        user_pending_emoji = app_config["channel"]["reaction"]["user"]["pending"]
        expert_pending_emoji = app_config["channel"]["reaction"]["expert"]["pending"]
        message_english = message.message_context.message_english_text
        chunks_list = await self.__aretrieve_chunks_list(message_english, k=3)
        user_prompt = self.__get_user_prompt(", ".join(chunks_list), message_english)
        augmented_prompts = self.__augment(user_prompt)
        llm_response, response_text = await llm_client.agenerate_response(augmented_prompts)
        byoeb_user_message = await self.__get_new_user_message(
            message,
            response_text,
            self.USER_PENDING_EMOJI
        )
        if byoeb_user_message.message_context.additional_info is None:
            print("No additional info")
        print("Additional info")
        byoeb_expert_message = self.__get_new_expert_verification_message(
            message,
            response_text,
            self.EXPERT_PENDING_EMOJI,
            self.PENDING
        )
        
        if self._successor:
            return await self._successor.handle([byoeb_user_message, byoeb_expert_message])


class ByoebExpertGenerateResponse(Handler):

    EXPERT_DEFAULT_MESSAGE = bot_config["template_messages"]["expert"]["default"]
    EXPERT_THANK_YOU_MESSAGE = bot_config["template_messages"]["expert"]["thank_you"]
    EXPERT_ASK_FOR_CORRECTION = bot_config["template_messages"]["expert"]["ask_for_correction"]

    USER_VERIFIED_ANSWER_MESSAGE = bot_config["template_messages"]["user"]["verified_answer"]
    USER_WRONG_ANSWER_MESSAGE = bot_config["template_messages"]["user"]["wrong_answer"]
    USER_CORRECTED_ANSWER_MESSAGE = bot_config["template_messages"]["user"]["corrected_answer"]

    VERIFICATION_STATUS = "verification_status"
    PENDING = "pending"
    WAITING = "waiting"
    RESOLVED = "resolved"

    USER_VERIFIED_EMOJI = app_config["channel"]["reaction"]["user"]["verified"]
    USER_REJECTED_EMOJI = app_config["channel"]["reaction"]["user"]["rejected"]
    USER_PENDING_EMOJI = app_config["channel"]["reaction"]["user"]["pending"]

    EXPERT_RESOLVED_EMOJI = app_config["channel"]["reaction"]["expert"]["resolved"]
    EXPERT_PENDING_EMOJI = app_config["channel"]["reaction"]["expert"]["pending"]
    EXPERT_WAITING_EMOJI = app_config["channel"]["reaction"]["expert"]["waiting"]

    def __parse_message(self, message: str) -> dict:
        pattern = r"\*Question\*:\s*(.*?)\n\*Bot_Answer\*:\s*(.*)"
        match = re.search(pattern, message)
        if match:
            return {
                "Question": match.group(1).strip(),
                "Bot_Answer": match.group(2).strip()
            }
        return {}
    
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
    
    def __get_user_message(
        self,
        text_message: str,
        byoeb_message: ByoebMessageContext,
        emoji = None,
        status = None,
    ):
        user_info_dict = byoeb_message.cross_conversation_context.get("user")
        user = User.model_validate(user_info_dict)
        user_reply_to_messages_context = byoeb_message.cross_conversation_context.get("messages_context")
        user_reply_to_message_context = None
        for message_context_dict in user_reply_to_messages_context:
            message_context = MessageContext.model_validate(message_context_dict)
            if message_context.message_type == MessageTypes.REGULAR_TEXT.value:
                user_reply_to_message_context = message_context
                break
        new_user_message = ByoebMessageContext(
            channel_type=byoeb_message.channel_type,
            message_category=MessageCategory.BOT_TO_USER_RESPONSE.value,
            user=user,
            message_context=MessageContext(
                message_type=MessageTypes.REGULAR_TEXT.value,
                message_source_text=text_message,
                message_english_text=text_message,
            ),
            additional_info={
                "emoji": emoji,
                self.VERIFICATION_STATUS: status
            },
            reply_context=ReplyContext(
                reply_id=user_reply_to_message_context.message_id,
            )
        )
        return new_user_message
    
    def __get_expert_message(
        self,
        text_message: str,
        byoeb_message: ByoebMessageContext,
        emoji = None,
        status = None,
    ):
        new_expert_message = ByoebMessageContext(
            channel_type=byoeb_message.channel_type,
            message_category=MessageCategory.BOT_TO_EXPERT.value,
            user=User(
                user_id=byoeb_message.user.user_id,
                user_language=byoeb_message.user.user_language,
                phone_number_id=byoeb_message.user.phone_number_id
            ),
            message_context=MessageContext(
                message_type=MessageTypes.REGULAR_TEXT.value,
                message_source_text=text_message,
                message_english_text=text_message,
                additional_info={
                    "emoji": emoji,
                    self.VERIFICATION_STATUS: status
                }
            ),
            reply_context=ReplyContext(
                reply_id=byoeb_message.reply_context.reply_id,
            ),
            incoming_timestamp=byoeb_message.incoming_timestamp,
        )
        return new_expert_message
        
    async def handle(
        self,
        messages: List[ByoebMessageContext]
    ):
        message = messages[0]
        from byoeb.app.configuration.dependency_setup import llm_client
        reply_context = message.reply_context
        byoeb_expert_message = None
        byoeb_user_message = None
        button_titles = bot_config["template_messages"]["expert"]["verification"]["button_titles"]
        yes = button_titles[0]
        no = button_titles[1]
        if reply_context is None:
            byoeb_expert_message = self.__get_expert_message(self.EXPERT_DEFAULT_MESSAGE, message)

        elif (reply_context.message_category == MessageCategory.BOT_TO_EXPERT_VERIFICATION.value
            and reply_context.additional_info[self.VERIFICATION_STATUS] == self.PENDING
            and message.message_context.message_english_text not in button_titles):
            byoeb_expert_message = self.__get_expert_message(self.EXPERT_DEFAULT_MESSAGE, message)

        elif (reply_context.message_category == MessageCategory.BOT_TO_EXPERT_VERIFICATION.value
            and reply_context.additional_info[self.VERIFICATION_STATUS] == self.PENDING
            and message.message_context.message_english_text == yes):
            byoeb_expert_message = self.__get_expert_message(
                self.EXPERT_THANK_YOU_MESSAGE,
                message,
                self.EXPERT_RESOLVED_EMOJI,
                self.RESOLVED
            )
            byoeb_user_message = self.__get_user_message(
                self.USER_VERIFIED_ANSWER_MESSAGE,
                message,
                self.USER_VERIFIED_EMOJI
            )

        elif (reply_context.message_category == MessageCategory.BOT_TO_EXPERT_VERIFICATION.value
            and reply_context.additional_info[self.VERIFICATION_STATUS] == self.PENDING
            and message.message_context.message_english_text == no):
            byoeb_expert_message = self.__get_expert_message(
                self.EXPERT_ASK_FOR_CORRECTION,
                message,
                self.EXPERT_WAITING_EMOJI,
                self.WAITING)
            byoeb_user_message = self.__get_user_message(
                self.USER_WRONG_ANSWER_MESSAGE,
                message,
                self.USER_REJECTED_EMOJI
            )

        elif (reply_context.message_category == MessageCategory.BOT_TO_EXPERT_VERIFICATION.value
            and reply_context.additional_info[self.VERIFICATION_STATUS] == self.WAITING
        ):
            correction = message.message_context.message_english_text
            verification_message = reply_context.reply_english_text
            parsed_message = self.__parse_message(verification_message)
            user_prompt = self.__get_user_prompt(
                parsed_message["Question"],
                parsed_message["Bot_Answer"],
                correction
            )
            augmented_prompts = self.__augment(user_prompt)
            llm_response, response_text = await llm_client.agenerate_response(augmented_prompts)
            corrected_answer = self.USER_CORRECTED_ANSWER_MESSAGE.replace("<CORRECTED_ANSWER>", response_text)
            byoeb_expert_message = self.__get_expert_message(
                self.EXPERT_THANK_YOU_MESSAGE,
                message,
                self.EXPERT_RESOLVED_EMOJI,
                self.RESOLVED)
            byoeb_user_message = self.__get_user_message(
                corrected_answer,
                message,
                self.USER_VERIFIED_EMOJI,
                self.RESOLVED
            )

        if self._successor:
            return await self._successor.handle([byoeb_user_message, byoeb_expert_message])