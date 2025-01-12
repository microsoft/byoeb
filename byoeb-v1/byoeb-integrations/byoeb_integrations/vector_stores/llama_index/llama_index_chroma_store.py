import os
from typing import List
from byoeb_core.models.vector_stores.chunk import Chunk
from byoeb_core.vector_stores.base import BaseVectorStore
from byoeb_integrations.vector_stores.chroma.base import ChromaDBVectorStore
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import VectorStoreIndex
from llama_index.core.schema import TextNode

class LlamaIndexChromaDBStore(BaseVectorStore):
    def __init__(
        self,
        persist_directory: str,
        collection_name: str,
        embedding_function=None
    ):
        
        self.__persist_directory = persist_directory
        self.__collection_name = collection_name
        self.__embedding_function = embedding_function
        self.chromadb = ChromaDBVectorStore(
            self.__persist_directory,
            self.__collection_name
        )
        self.vector_store_index = None
        self.__get_or_create_store()
        
    
    def __get_or_create_store(
        self
    ):
        if self.vector_store_index is not None:
            return self.vector_store_index
        self.collection = self.chromadb.get_or_create_collection()
        os.chmod(self.__persist_directory, 0o777)
        self.vector_store = ChromaVectorStore(chroma_collection=self.collection)
        self.vector_store_index = VectorStoreIndex.from_vector_store(
            vector_store=self.vector_store,
            embed_model=self.__embedding_function
        )
        return self.vector_store_index
    
    def add_nodes(
        self,
        nodes: List[TextNode],
        show_progress: bool = False
    ):
        vector_store_index = self.__get_or_create_store()
        vector_store_index.insert_nodes(
            nodes,
            show_progress=show_progress
        )

    def delete_nodes(
        self,
        ids: List[str],
        show_progress: bool = False
    ):
        vector_store_index = self.__get_or_create_store()
        vector_store_index.delete_nodes(
            ids,
            show_progress=show_progress
        )

    def add_chunks(
        self,
        data_chunks: list, 
        metadata: list,
        ids: list = None,
        **kwargs
    ):
        if len(data_chunks) != len(metadata):
            raise ValueError("Data chunks and metadata should be of the same length")
        nodes = []
        for i, _ in enumerate(data_chunks):
            text_node = TextNode(
                text=data_chunks[i],
                metadata=metadata[i],
            )
            nodes.append(text_node)
        self.add_nodes(nodes)

    def update_chunks(
        self,
        data_chunks: list,
        metadata: list,
        ids: list,
        **kwargs
    ):
        raise NotImplementedError
    
    def delete_chunks(
        self,
        ids: list,
        **kwargs
    ):
        self.delete_nodes(ids)

    def retrieve_top_k_chunks(
        self,
        text: str,
        k: int,
        **kwargs
    ):
        vector_store_index = self.__get_or_create_store()
        retriever = vector_store_index.as_retriever(similarity_top_k=k)
        nodes = retriever.retrieve(text)
        chunk_list: List[Chunk] = []
        for node in nodes:
            chunk = Chunk(
                chunk_id=node.node.node_id,
                text=node.node.text,
                metadata=node.node.metadata
            )
            chunk_list.append(chunk)
        return chunk_list
    
    async def aretrieve_top_k_chunks(
        self,
        text: str,
        k: int,
        **kwargs
    ):
        vector_store_index = self.__get_or_create_store()
        retriever = vector_store_index.as_retriever(similarity_top_k=k)
        nodes = await retriever.aretrieve(text)
        chunk_list: List[Chunk] = []
        for node in nodes:
            chunk = Chunk(
                chunk_id=node.node.node_id,
                text=node.node.text,
                metadata=node.node.metadata
            )
            chunk_list.append(chunk)
        return chunk_list
    
    def delete_store(self):
        if self.vector_store_index is not None:
            self.chromadb.delete_store()
        self.vector_store_index = None
    
