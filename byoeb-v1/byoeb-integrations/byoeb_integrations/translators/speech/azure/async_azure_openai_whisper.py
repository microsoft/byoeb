
import io
import os
import azure.cognitiveservices.speech as speechsdk
from openai import AsyncAzureOpenAI
from byoeb_core.translators.speech.base import BaseSpeechTranslator
from typing import Any

class AsyncAzureOpenAIWhisper(BaseSpeechTranslator):
    
    def __init__(
        self,
        model: str,
        azure_endpoint: str,
        token_provider: str = None,
        api_key: str = None,
        api_version: str = None,
        **kwargs
    ):
        client = None
        if model is None:
            raise ValueError("model must be provided")
        if api_version is None:
            raise ValueError("api_version must be provided")
        if azure_endpoint is None:
            raise ValueError("azure_endpoint must be provided")
        if token_provider is not None:
            client = AsyncAzureOpenAI(
                azure_endpoint=azure_endpoint,
                azure_ad_token_provider=token_provider,
                api_version=api_version
            )
        elif api_key is not None:
            client = AsyncAzureOpenAI(
                api_key=api_key,
                azure_endpoint=azure_endpoint,
                api_version=api_version
            )
        else:
            raise ValueError("Either token_provider or api_key must be provided")
        
        self.__model = model
        self.__client = client

    def speech_to_text(
        self,
        audio_file: str,
        source_language: str,
        **kwargs
    ) -> Any:
        raise NotImplementedError
    
    async def aspeech_to_text(
        self,
        audio_data: bytes,
        source_language: str = None,
        **kwargs
    ) -> str:
        audio_file_like = io.BytesIO(audio_data)
        audio_file_like.name = "temp.wav"
        result = await self.__client.audio.transcriptions.create(
            file=audio_file_like,
            model=self.__model,
        )
        return result.text

        
    def text_to_speech(
        self,
        input_text: str,
        source_language: str, 
        **kwargs
    ) -> Any:
        raise NotImplementedError

    async def atext_to_speech(
        self,
        input_text: str,
        source_language: str,
        **kwargs
    ) -> bytes:
        raise NotImplementedError
    