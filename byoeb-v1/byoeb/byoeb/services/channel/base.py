from abc import ABC, abstractmethod
from typing import List, Any, Dict
from byoeb_core.models.byoeb.message_context import ByoebMessageContext

class BaseChannelService(ABC):
    @abstractmethod
    def prepare_requests(
        self,
        byoeb_message: Any
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def prepare_reaction_requests(
        self,
        reaction: Any,
        responses: Any
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def send_requests(self, requests: Dict[str, Any]) -> Any:
        pass

    @abstractmethod
    async def create_bot_to_user_db_entries(
        self,
        byoeb_message: Any, 
        responses: Any
    ) -> List[ByoebMessageContext]:
        pass

    @abstractmethod
    async def create_cross_conv_db_entries(
        self,
        byoeb_user_message: ByoebMessageContext,
        byoeb_expert_message: ByoebMessageContext,
        user_responses: Any,
        expert_responses: Any
    ) -> List[ByoebMessageContext]:
        pass

