from abc import ABC, abstractmethod
from typing import Any

class BaseSpeechTranslator(ABC):
    @abstractmethod
    def speech_to_text(
        self,
        audio_file: str,
        source_language: str,
        **kwargs
    ) -> Any:
        pass

    @abstractmethod
    async def aspeech_to_text(
        self,
        audio_file: bytes,
        source_language: str,
        **kwargs
    ) -> str:
        pass

    @abstractmethod
    def text_to_speech(
        self,
        input_text: str,
        source_language: str,
        **kwargs
    ) -> bytes:
        pass
    
    @abstractmethod
    async def atext_to_speech(
        self,
        input_text: str,
        source_language: str,
        **kwargs
    ) -> bytes:
        pass