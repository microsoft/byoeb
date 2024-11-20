from abc import ABC, abstractmethod
from typing import Any


class BaseVectorStore(ABC):

    @abstractmethod
    def add_chunks(
        self,
        data_chunks: list, 
        metadata: list,
        ids: list,
        **kwargs
    ) -> Any:
        pass

    @abstractmethod
    def update_chunks(
        self,
        data_chunks: list, 
        metadata: list,
        ids: list,
        **kwargs
    ) -> Any:
        pass
    
    @abstractmethod
    def delete_chunks(
        self,
        ids: list,
        **kwargs
    ) -> Any:
        pass

    @abstractmethod
    def retrieve_top_k_chunks(
        self,
        text: str,
        k: int,
        **kwargs
    ) -> Any:
        pass
    
    async def aretrieve_top_k_chunks(
        self,
        text: str,
        k: int,
        **kwargs
    ) -> Any:
        return NotImplementedError
    
    @abstractmethod
    def delete_store(self):
        pass


