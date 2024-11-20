from abc import ABC, abstractmethod
from typing import Any, Dict
from byoeb_core.models.byoeb.response import ByoebResponseModel

class BaseChannelRegister(ABC):
    @abstractmethod
    async def register(
        self,
        request: str,
        **kwargs
    )-> ByoebResponseModel:
        pass

class BaseChannel(ABC):
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
    def recieve_message(
        self,
        **kwargs
    ) -> Any:
        pass

    @abstractmethod
    async def arecieve_message(
        self,
        **kwargs
    ) -> Any:
        pass

    @abstractmethod
    async def areply_to_message(
        self,
        message: Any,
        **kwargs
    ) -> Any:
        pass

    @abstractmethod
    async def asend_reaction(
        self,
        reactions,
        **kwargs
    ) -> Any:
        pass

    @abstractmethod
    async def asend_template(
        self,
        template: Any,
        **kwargs
    ) -> Any:
        pass

    @abstractmethod
    async def asend_poll(
        self,
        poll: Any,
        **kwargs
    ) -> Any:
        pass

    async def asend_interactive_message(
        self,
        message: Any,
        **kwargs
    ) -> Any:
        pass