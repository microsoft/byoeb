from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseDocumentDatabase(ABC):

    @abstractmethod
    def get_collection(
        self,
        collection_name: str
    ) -> Any:
        pass
    
    @abstractmethod
    async def aget_collection(
        self,
        collection_name: str
    ) -> Any:
        pass

    @abstractmethod
    def delete_collection(
        self,
        collection_name: str
    ) -> Any:
        pass

    @abstractmethod
    async def adelete_collection(
        self,
        collection_name: str
    ) -> Any:
        pass

class BaseDocumentCollection(ABC):
    @abstractmethod
    def insert(
        self,
        data: Any,
        **kwargs
    ) -> Any:
        pass

    @abstractmethod
    async def ainsert(
        self,
        data: Any,
        **kwargs
    ) -> Any:
        pass
    
    @abstractmethod
    def fetch(
        self,
        query: Dict[str, Any],
        **kwargs
    ) -> Any:
        pass

    @abstractmethod
    async def afetch(
        self,
        query: Dict[str, Any],
        **kwargs
    ) -> Any:
        pass
    
    @abstractmethod
    def fetch_all(
        self,
        query,
        **kwargs
    ) -> Any:
        pass

    @abstractmethod
    async def afetch_all(
        self,
        query,
        **kwargs
    ) -> Any:
        pass

    @abstractmethod
    async def afetch_ids(
        self,
        query,
        **kwargs
    ) -> Any:
        pass
    
    @abstractmethod
    def update(
        self,
        query: Dict[str, Any],
        update_data: Dict[str, Any],
        **kwargs
    ) -> Any:
        pass

    @abstractmethod
    async def aupdate(
        self,
        query: Dict[str, Any],
        update_data: Dict[str, Any],
        **kwargs
    ) -> Any:
        pass

    @abstractmethod
    def delete(
        self,
        query: Dict[str, Any],
        **kwargs
    ) -> Any:
        pass

    @abstractmethod
    async def adelete(
        self,
        query: Dict[str, Any],
        **kwargs
    ) -> Any:
        pass
