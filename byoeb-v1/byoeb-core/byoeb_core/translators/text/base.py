from abc import ABC, abstractmethod
from typing import Any

class BaseTextTranslator(ABC):
    @abstractmethod
    def translate_text(
        self,
        input_text: str,
        source_language: str,
        target_language: str,
        **kwargs
    ) -> Any:
        pass
    
    @abstractmethod
    async def atranslate_text(
        self,
        input_text: str,
        source_language: str,
        target_language: str,
        **kwargs
    ) -> Any:
        pass