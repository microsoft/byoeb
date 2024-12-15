from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import List, Any, Dict
from byoeb_core.models.byoeb.message_context import ByoebMessageContext

class MessageReaction(BaseModel):
    reaction: str
    message_id: str
    phone_number_id: str

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
        message_reactions = List[MessageReaction]
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

