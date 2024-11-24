from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseUserService(ABC):
    @abstractmethod
    async def aregister(
        self,
        users: list
    ) -> Any:
        pass

    @abstractmethod
    async def aget(
        self,
        phone_number_ids: Any
    ) -> Any:
        pass

    @abstractmethod
    async def aupdate(
        self,
        data: str
    ) -> Any:
        pass

    @abstractmethod
    async def adelete(
        self,
        phone_number_ids: Any
    ) -> Any:
        pass