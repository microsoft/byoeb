from abc import ABC, abstractmethod
from typing import Any, List
from byoeb_core.models.byoeb.message_context import ByoebMessageContext

class Handler(ABC):
    """Abstract Handler class."""
    
    def __init__(self, successor=None):
        self._successor = successor  # Next handler in the chain
    
    @abstractmethod
    async def handle(self, messages: list) -> Any:
        """Handle the message or pass it to the successor."""
        pass