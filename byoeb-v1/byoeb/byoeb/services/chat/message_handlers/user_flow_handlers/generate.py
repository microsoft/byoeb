import hashlib
import byoeb.services.chat.constants as constants
import re
import byoeb.utils.utils as utils
import random
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
from typing import List, Dict, Any
from byoeb.chat_app.configuration.config import bot_config, app_config
from byoeb.models.message_category import MessageCategory
from byoeb_core.models.vector_stores.chunk import Chunk
from byoeb_core.models.vector_stores.azure.azure_search import AzureSearchNode
from byoeb_core.models.byoeb.message_context import (
    ByoebMessageContext,
    MessageContext,
    ReplyContext,
    MessageTypes
)
from byoeb_integrations.vector_stores.azure_vector_search.azure_vector_search import AzureVectorSearchType
from byoeb_core.models.byoeb.user import User
from byoeb.services.chat.message_handlers.base import Handler
from byoeb.chat_app.configuration.dependency_setup import llm_client

class ByoebUserGenerateResponse(Handler):
    EXPERT_PENDING_EMOJI = app_config["channel"]["reaction"]["expert"]["pending"]
    USER_PENDING_EMOJI = app_config["channel"]["reaction"]["user"]["pending"]
    _expert_user_types = bot_config["expert"]
    _regular_user_type = bot_config["regular"]["user_type"]

    async def __aretrieve_chunks(
        self,
        text,
        k
    ) -> List[Chunk]:
        from byoeb.chat_app.configuration.dependency_setup import vector_store
        start_time = datetime.now().timestamp()
        retrieved_chunks = await vector_store.aretrieve_top_k_chunks(
            text,
            k,
            search_type=AzureVectorSearchType.DENSE.value,
            select=["id", "text", "metadata", "related_questions"],
            vector_field="text_vector_3072"
        )
        end_time = datetime.now().timestamp()
        utils.log_to_text_file(f"Retrieved chunks in {end_time - start_time} seconds")
        return retrieved_chunks
        
    def __augment(
        self,
        system_prompt,
        user_prompt
    ):
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
    
    def __create_read_reciept_message(
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
            description = bot_config["template_messages"]["user"]["follow_up_questions_description"][user_language]
            user_lang_related_questions = [
                await text_translator.atranslate_text(
                    input_text=question,
                    source_language="en",
                    target_language=user_language
                )
                for question in related_questions
            ]

            interactive_list_additional_info = {
                constants.DESCRIPTION: description,
                constants.ROW_TEXTS: user_lang_related_questions
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
                    user_type=self._regular_user_type,
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
        query_type = "medical",
        emoji = None,
        status = None,
    ) -> ByoebMessageContext:
        
        expert_phone_number_id , expert_type= self.__get_expert_number_and_type(message.user.experts, query_type)
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
    
    @retry(
        stop=stop_after_attempt(3),  # Retry up to 3 times
        wait=wait_exponential(multiplier=1, max=10),  # Exponential backoff with a max wait time of 10 seconds
    )
    async def agenerate_answer(
        self,
        question,
        retrieved_chunks: List[Chunk],
    ):
        def parse_response(response_text):
            # Regular expressions to extract the response and relevance
            response_pattern = r"<BEGIN RESPONSE>(.*?)<END RESPONSE>"
            query_type_pattern = r"<BEGIN QUERY TYPE>(.*?)<END QUERY TYPE>"

            # Extract the response
            response_match = re.search(response_pattern, response_text, re.DOTALL)
            response = response_match.group(1).strip() if response_match else None

            # Extract the relevance
            query_type_match = re.search(query_type_pattern, response_text, re.DOTALL)
            query_type = query_type_match.group(1).strip() if query_type_match else None
            return response, query_type
        
        chunks_list = [chunk.text for chunk in retrieved_chunks]
        system_prompt = bot_config["llm_response"]["answer_prompts"]["system_prompt"]
        template_user_prompt = bot_config["llm_response"]["answer_prompts"]["user_prompt"]
        # Replace placeholders with actual values
        chunks = ", ".join(chunks_list)
        user_prompt = template_user_prompt.replace("<CHUNKS>", chunks).replace("<QUESTION>", question)
        augmented_prompts = self.__augment(system_prompt, user_prompt)
        llm_response, response_text = await llm_client.agenerate_response(augmented_prompts)
        tokens = llm_client.get_response_tokens(llm_response)
        utils.log_to_text_file(f"Generated answer tokens: {str(tokens)}")
        answer, query_type = parse_response(response_text)
        print("Generated answer: ", answer)
        print("Query type: ", query_type)
        if answer is None or query_type is None:
            raise ValueError("Parsing failed, response or query_type is None.")
        return answer, query_type
    
    @retry(
        stop=stop_after_attempt(3),  # Retry up to 3 times
        wait=wait_exponential(multiplier=1, max=10),  # Exponential backoff with a max wait time of 10 seconds
    )
    async def agenerate_follow_up_questions(
        self,
        retrieved_chunks: List[Chunk],
    ):
        chunks_list = [chunk.text for chunk in retrieved_chunks]
        system_prompt = bot_config["llm_response"]["follow_up_prompts"]["system_prompt"]
        template_user_prompt = bot_config["llm_response"]["follow_up_prompts"]["user_prompt"]
        chunks = ", ".join(chunks_list)
        user_prompt = template_user_prompt.replace("<CHUNKS>", chunks)
        augmented_prompts = self.__augment(system_prompt, user_prompt)
        llm_response, response_text = await llm_client.agenerate_response(augmented_prompts)
        tokens = llm_client.get_response_tokens(llm_response)
        utils.log_to_text_file(f"Generated answer tokens: {str(tokens)}")
        next_questions = re.findall(r"<q_\d+>(.*?)</q_\d+>", response_text)
        if next_questions is None or len(next_questions) != 3:
            raise ValueError("Parsing failed, next_questions.")
        return next_questions
    
    def get_follow_up_questions(
        self,
        user_lang_code: str,
        retrieved_chunks: List[Chunk],
    ):
        random_selection = []
        for retrieved_chunk in retrieved_chunks:
            related_questions = retrieved_chunk.related_questions.get(user_lang_code)
            if related_questions is not None:
                random_selection.append(random.choice(related_questions))
        return random_selection
    
    async def __handle_message_generate_workflow(
        self,
        messages: ByoebMessageContext
    ) -> List[ByoebMessageContext]:
        message: ByoebMessageContext = messages[0].model_copy(deep=True)
        read_reciept_message = self.__create_read_reciept_message(message)
        message_english = message.message_context.message_english_text
        retrieved_chunks = await self.__aretrieve_chunks(message_english, k=3)
        answer, query_type = await self.agenerate_answer(message_english, retrieved_chunks)
        related_questions = self.get_follow_up_questions(message.user.user_language, retrieved_chunks)
        byoeb_user_message = await self.__create_user_message(
            message=message,
            response_text=answer,
            emoji=self.USER_PENDING_EMOJI,
            status=constants.PENDING,
            related_questions=related_questions
        )
        byoeb_expert_message = self.__create_expert_verification_message(
            message,
            answer,
            query_type,
            self.EXPERT_PENDING_EMOJI,
            constants.PENDING
        )
        return [byoeb_user_message, byoeb_expert_message, read_reciept_message]
    
    async def handle(
        self,
        messages: List[ByoebMessageContext]
    ) -> Dict[str, Any]:
        if messages is None or len(messages) == 0:
            return {}
        new_messages = []
        try:
            start_time = datetime.now().timestamp()
            new_messages = await self.__handle_message_generate_workflow(messages)
            end_time = datetime.now().timestamp()
            utils.log_to_text_file(f"Generated answer and related questions in {end_time - start_time} seconds")
        except RetryError as e:
            utils.log_to_text_file(f"RetryError in generating response: {e}")
            print("RetryError in generating response: ", e)
            raise e
        except Exception as e:
            utils.log_to_text_file(f"Error in generating response: {e}")
            print("Error in generating response: ", e)
            raise e
        if self._successor:
            return await self._successor.handle(
                new_messages
            )