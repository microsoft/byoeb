from abc import ABC, abstractmethod
from typing import Any


class BaseEmbedding(ABC):
    @abstractmethod
    def get_embedding_function(
        self,
        **kwargs
    ) -> Any:
        pass