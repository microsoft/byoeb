from abc import ABC, abstractmethod
from typing import Any

class BaseLLM(ABC):
    @abstractmethod
    def generate_response(self, query: str) -> Any:
        pass

    @abstractmethod
    async def agenerate_response(
        self,
        prompts,
        **kwargs
    ) -> Any:
        pass
    @abstractmethod
    def get_llm_client(self) -> Any:
        pass