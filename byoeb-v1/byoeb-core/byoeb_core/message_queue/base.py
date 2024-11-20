from abc import ABC, abstractmethod
from typing import Any

class BaseQueue(ABC):
    @abstractmethod
    def send_message(
        self,
        message: Any,
        **kwargs
    ) -> Any:
        pass
    @abstractmethod
    async def asend_message(
        self,
        message: Any,
        **kwargs
    ) -> Any:
        pass
    @abstractmethod
    def receive_message(
        self,
        **kwargs
    ) -> Any:
        pass
    @abstractmethod
    async def areceive_message(
        self,
        **kwargs
    ) -> Any:
        pass

    @abstractmethod
    def delete_message(
        self,
        message,
        **kwargs
    ) -> Any:
        pass
    @abstractmethod
    async def adelete_message(
        self,
        message,
        **kwargs
    ) -> Any:
        pass