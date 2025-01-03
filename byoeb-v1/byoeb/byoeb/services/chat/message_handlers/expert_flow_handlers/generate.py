import re
import json
import byoeb.services.chat.constants as constants
from typing import List, Dict, Any
from datetime import datetime
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

class ByoebExpertGenerateResponse(Handler):

    EXPERT_DEFAULT_MESSAGE = bot_config["template_messages"]["expert"]["default"]
    EXPERT_THANK_YOU_MESSAGE = bot_config["template_messages"]["expert"]["thank_you"]
    EXPERT_ASK_FOR_CORRECTION = bot_config["template_messages"]["expert"]["ask_for_correction"]
    EXPERT_ALREADY_VERIFIED_MESSAGE = bot_config["template_messages"]["expert"]["already_answered"]

    USER_VERIFIED_ANSWER_MESSAGES = bot_config["template_messages"]["user"]["verified_answer"]
    USER_WRONG_ANSWER_MESSAGES = bot_config["template_messages"]["user"]["wrong_answer"]
    USER_CORRECTED_ANSWER_MESSAGES = bot_config["template_messages"]["user"]["corrected_answer"]

    USER_VERIFIED_EMOJI = app_config["channel"]["reaction"]["user"]["verified"]
    USER_REJECTED_EMOJI = app_config["channel"]["reaction"]["user"]["rejected"]
    USER_PENDING_EMOJI = app_config["channel"]["reaction"]["user"]["pending"]

    EXPERT_RESOLVED_EMOJI = app_config["channel"]["reaction"]["expert"]["resolved"]
    EXPERT_PENDING_EMOJI = app_config["channel"]["reaction"]["expert"]["pending"]
    EXPERT_WAITING_EMOJI = app_config["channel"]["reaction"]["expert"]["waiting"]

    _regular_user_type = bot_config["regular"]["user_type"]
    button_titles = bot_config["template_messages"]["expert"]["verification"]["button_titles"]
    yes = button_titles[0]
    no = button_titles[1]

    def __get_user_language(
        self,
        user_info_dict: dict
    ):
        user = User.model_validate(user_info_dict)
        return user.user_language

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
    
    def __create_user_reply_context(
        self,
        byoeb_message: ByoebMessageContext,
        cross_conv_message: ByoebMessageContext,
        emoji = None,
        status = None
    ) -> ReplyContext:
        reply_id = cross_conv_message.message_context.message_id
        reply_type = cross_conv_message.message_context.message_type
        reply_additional_info = {
            constants.UPDATE_ID: cross_conv_message.message_context.message_id,
            constants.EMOJI: emoji,
            constants.VERIFICATION_STATUS: status,
            constants.MODIFIED_TIMESTAMP: str(int(datetime.now().timestamp()))
        }
        if (status == constants.VERIFIED
            and byoeb_message.reply_context.additional_info[constants.VERIFICATION_STATUS] == constants.WAITING
        ):
            reply_id = cross_conv_message.reply_context.reply_id
            reply_type = None
            reply_additional_info = {
                constants.UPDATE_ID: cross_conv_message.message_context.message_id,
                constants.VERIFICATION_STATUS: status,
                constants.MODIFIED_TIMESTAMP: str(int(datetime.now().timestamp()))
            }

        return ReplyContext(
            reply_id=reply_id,
            reply_type=reply_type,
            additional_info=reply_additional_info
        )
    
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
        text_message: str,
        byoeb_message: ByoebMessageContext,
        emoji = None,
        status = None,
    ):
        from byoeb.chat_app.configuration.dependency_setup import speech_translator
        from byoeb.chat_app.configuration.dependency_setup import text_translator
        user_info_dict = byoeb_message.cross_conversation_context.get(constants.USER)
        user = User.model_validate(user_info_dict)
        user.user_type = self._regular_user_type
        reply_to_user_messages_context = byoeb_message.cross_conversation_context.get(constants.MESSAGES_CONTEXT)
        reply_to_user_message_context = None
        message_reaction_additional_info = {}
        media_additiona_info = {}
        message_en_text = None
        if (status == constants.VERIFIED
            and byoeb_message.reply_context.additional_info[constants.VERIFICATION_STATUS] == constants.WAITING
        ):
            message_en_text = text_message
            translated_text = await text_translator.atranslate_text(
                input_text=text_message,
                source_language="en",
                target_language=user.user_language
            )
            text_message = self.USER_CORRECTED_ANSWER_MESSAGES.get(user.user_language).replace("<CORRECTED_ANSWER>", translated_text)
            translated_audio_message = await speech_translator.atext_to_speech(
                input_text=text_message,
                source_language=user.user_language,
            )
            media_additiona_info = {
                constants.DATA: translated_audio_message,
                constants.MIME_TYPE: "audio/wav"
            }
            message_reaction_additional_info = {
                constants.EMOJI: emoji,
                constants.VERIFICATION_STATUS: status
            }
        new_user_messages = []
        for message_context_dict in reply_to_user_messages_context:
            reply_to_user_message_context = ByoebMessageContext.model_validate(message_context_dict)
            reply_context = self.__create_user_reply_context(
                byoeb_message,
                reply_to_user_message_context,
                emoji,
                status
            )
            print("Reply context: ", json.dumps(reply_context.model_dump()))
            message_context = None
            if (reply_to_user_message_context.message_context.message_type == MessageTypes.REGULAR_AUDIO.value):
                message_context = MessageContext(
                    message_type=MessageTypes.REGULAR_AUDIO.value,
                    additional_info={
                        **media_additiona_info,
                        **message_reaction_additional_info
                    }
                )
            elif reply_to_user_message_context.message_context.message_type == MessageTypes.INTERACTIVE_LIST.value:
                description = bot_config["template_messages"]["user"]["follow_up_questions_description"][user.user_language]
                related_questions = reply_to_user_message_context.message_context.additional_info.get(constants.RELATED_QUESTIONS)
                message_context = MessageContext(
                    message_type=MessageTypes.REGULAR_TEXT.value,
                    message_english_text=message_en_text,
                    message_source_text=text_message,
                    additional_info={
                        **message_reaction_additional_info,
                        constants.DESCRIPTION: description,
                        constants.ROW_TEXTS: related_questions
                    }
                )
            # print("Message context: ", json.dumps(message_context.model_dump()))
            
            new_user_message = ByoebMessageContext(
                channel_type=byoeb_message.channel_type,
                message_category=MessageCategory.BOT_TO_USER_RESPONSE.value,
                user=user,
                message_context=message_context,
                reply_context=reply_context
            )
            new_user_messages.append(new_user_message)
        return new_user_messages
    
    def __create_expert_message(
        self,
        text_message: str,
        byoeb_message: ByoebMessageContext,
        emoji = None,
        status = None,
    ):
        correction_info = {}

        if (status == constants.VERIFIED
            and byoeb_message.message_context.message_source_text != self.yes
        ):
            correction_source = byoeb_message.message_context.message_source_text
            correction_english = byoeb_message.message_context.message_english_text
            correction_info = {
                constants.CORRECTION_SOURCE: correction_source,
                constants.CORRECTION_EN: correction_english
            }
        new_expert_message = ByoebMessageContext(
            channel_type=byoeb_message.channel_type,
            message_category=MessageCategory.BOT_TO_EXPERT.value,
            user=User(
                user_id=byoeb_message.user.user_id,
                user_type=byoeb_message.user.user_type,
                user_language=byoeb_message.user.user_language,
                phone_number_id=byoeb_message.user.phone_number_id
            ),
            message_context=MessageContext(
                message_type=MessageTypes.REGULAR_TEXT.value,
                message_source_text=text_message,
                message_english_text=text_message,
            ),
            reply_context=ReplyContext(
                reply_id=byoeb_message.reply_context.reply_id,
                additional_info={
                    constants.EMOJI: emoji,
                    constants.VERIFICATION_STATUS: status,
                    **correction_info,
                    constants.MODIFIED_TIMESTAMP: str(int(datetime.now().timestamp()))
                }
            ),
            cross_conversation_context=byoeb_message.cross_conversation_context,
            incoming_timestamp=byoeb_message.incoming_timestamp,
        )
        if new_expert_message.reply_context.reply_id is None:
            new_expert_message.reply_context = None
        return [new_expert_message]
    
    def __get_cross_conv_verification_status(
        self,
        message: ByoebMessageContext
    ):
        # Check if cross_conversation_context exists
        if not message.cross_conversation_context:
            return None

        # Retrieve cross_messages_context with necessary checks
        cross_messages_context = message.cross_conversation_context.get(constants.MESSAGES_CONTEXT)
        if not cross_messages_context:
            return None

        # Validate and extract the first message context
        cross_message_context = ByoebMessageContext.model_validate(cross_messages_context[0])

        if not cross_message_context.message_context:
            return None
        if not cross_message_context.message_context.additional_info:
            return None
        
        return cross_message_context.message_context.additional_info.get(constants.VERIFICATION_STATUS)
        
        
    async def handle(
        self,
        messages: List[ByoebMessageContext]
    ) -> Dict[str, Any]:
        message = messages[0]
        read_reciept_message = self.__get_read_reciept_message(message)
        from byoeb.chat_app.configuration.dependency_setup import llm_client
        reply_context = message.reply_context
        cross_message_verification_status = self.__get_cross_conv_verification_status(message)
        byoeb_expert_messages = []
        byoeb_user_messages = []
        byoeb_messages = []

        if reply_context is None or reply_context.reply_id is None:
            byoeb_expert_messages = self.__create_expert_message(self.EXPERT_DEFAULT_MESSAGE, message)

        elif cross_message_verification_status is None:
            byoeb_expert_messages = self.__create_expert_message(self.EXPERT_DEFAULT_MESSAGE, message)
        
        elif cross_message_verification_status == constants.VERIFIED:
            byoeb_expert_messages = self.__create_expert_message(self.EXPERT_ALREADY_VERIFIED_MESSAGE, message)

        elif (reply_context.message_category == MessageCategory.BOT_TO_EXPERT_VERIFICATION.value
            and reply_context.additional_info[constants.VERIFICATION_STATUS] == constants.PENDING
            and message.message_context.message_english_text not in self.button_titles):
            byoeb_expert_messages = self.__create_expert_message(self.EXPERT_DEFAULT_MESSAGE, message)

        elif (reply_context.message_category == MessageCategory.BOT_TO_EXPERT_VERIFICATION.value
            and reply_context.additional_info[constants.VERIFICATION_STATUS] == constants.PENDING
            and message.message_context.message_english_text == self.yes):
            byoeb_expert_messages = self.__create_expert_message(
                self.EXPERT_THANK_YOU_MESSAGE,
                message,
                self.EXPERT_RESOLVED_EMOJI,
                constants.VERIFIED
            )
            user_lang = self.__get_user_language(
                message.cross_conversation_context.get(constants.USER)
            )
            byoeb_user_messages = await self.__create_user_message(
                self.USER_VERIFIED_ANSWER_MESSAGES.get(user_lang),
                message,
                self.USER_VERIFIED_EMOJI,
                constants.VERIFIED
            )

        elif (reply_context.message_category == MessageCategory.BOT_TO_EXPERT_VERIFICATION.value
            and reply_context.additional_info[constants.VERIFICATION_STATUS] == constants.PENDING
            and message.message_context.message_english_text == self.no):
            byoeb_expert_messages = self.__create_expert_message(
                self.EXPERT_ASK_FOR_CORRECTION,
                message,
                self.EXPERT_WAITING_EMOJI,
                constants.WAITING)
            user_lang = self.__get_user_language(
                message.cross_conversation_context.get(constants.USER)
            )
            byoeb_user_messages = await self.__create_user_message(
                self.USER_WRONG_ANSWER_MESSAGES.get(user_lang),
                message,
                self.USER_REJECTED_EMOJI,
                constants.WRONG
            )

        elif (reply_context.message_category == MessageCategory.BOT_TO_EXPERT_VERIFICATION.value
            and reply_context.additional_info[constants.VERIFICATION_STATUS] == constants.WAITING
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
            print("Corrected answer: ", response_text)
            byoeb_expert_messages = self.__create_expert_message(
                self.EXPERT_THANK_YOU_MESSAGE,
                message,
                self.EXPERT_RESOLVED_EMOJI,
                constants.VERIFIED)
            byoeb_user_messages = await self.__create_user_message(
                response_text,
                message,
                self.USER_VERIFIED_EMOJI,
                constants.VERIFIED
            )
        byoeb_messages = byoeb_user_messages + byoeb_expert_messages + [read_reciept_message]
        if self._successor:
            return await self._successor.handle(byoeb_messages)