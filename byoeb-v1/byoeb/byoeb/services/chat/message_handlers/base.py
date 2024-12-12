from abc import ABC, abstractmethod
from typing import List
from byoeb_core.models.byoeb.message_context import ByoebMessageContext

class Handler(ABC):
    """Abstract Handler class."""
    
    def __init__(self, successor=None):
        self._successor = successor  # Next handler in the chain
    
    @abstractmethod
    def handle(self, messages: list) -> List[ByoebMessageContext]:
        """Handle the message or pass it to the successor."""
        pass