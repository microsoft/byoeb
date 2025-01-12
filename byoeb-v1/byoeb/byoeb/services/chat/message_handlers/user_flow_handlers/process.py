from typing import Dict, Any, List
from byoeb_core.models.byoeb.message_context import ByoebMessageContext, MessageTypes
from byoeb.services.chat.message_handlers.base import Handler

class ByoebUserProcess(Handler):

    async def __handle_process_message_workflow(
        self,
        messages: List[ByoebMessageContext]
    ) -> ByoebMessageContext:
        # dependency injection
        from byoeb.chat_app.configuration.dependency_setup import text_translator
        from byoeb.chat_app.configuration.dependency_setup import channel_client_factory
        from byoeb.chat_app.configuration.dependency_setup import speech_translator_whisper
        from byoeb_core.convertor.audio_convertor import ogg_opus_to_wav_bytes

        message = messages[0].model_copy(deep=True)
        channel_type = message.channel_type
        source_language = message.user.user_language
        translated_en_text = None

        if message.message_context.message_type == MessageTypes.REGULAR_AUDIO.value:
            media_id = message.message_context.media_info.media_id
            channel_client = await channel_client_factory.get(channel_type)
            _, audio_message, err = await channel_client.adownload_media(media_id)
            audio_message_wav = ogg_opus_to_wav_bytes(audio_message.data)
            audio_to_text = await speech_translator_whisper.aspeech_to_text(audio_message_wav, source_language)
            # print("audio_to_text", audio_to_text)
            translated_en_text = await text_translator.atranslate_text(
                input_text=audio_to_text,
                source_language=source_language,
                target_language="en"
            )
            message.message_context.media_info.media_type = audio_message.mime_type
        
        else:
            source_text = message.message_context.message_source_text
            translated_en_text = await text_translator.atranslate_text(
                input_text=source_text,
                source_language=source_language,
                target_language="en"
            )
            
        message.message_context.message_english_text = translated_en_text
        return message

    async def handle(
        self,
        messages: List[ByoebMessageContext]
    ) -> Dict[str, Any]:
        message = None
        try:
            message = await self.__handle_process_message_workflow(messages)
        except Exception as e:
            raise e
        
        if self._successor:
            return await self._successor.handle([message])