from abc import ABC, abstractmethod


class Handler(ABC):
    """Abstract Handler class."""
    
    def __init__(self, successor=None):
        self._successor = successor  # Next handler in the chain
    
    @abstractmethod
    def handle(self, request):
        """Handle the request or pass it to the successor."""
        pass