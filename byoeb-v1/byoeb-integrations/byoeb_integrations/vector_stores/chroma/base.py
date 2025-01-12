from typing import List
import chromadb
from chromadb.config import Settings
from byoeb_core.vector_stores.base import BaseVectorStore
from byoeb_core.models.vector_stores.chunk import Chunk
from chromadb.utils import embedding_functions

class ChromaDBVectorStore(BaseVectorStore):
    def __init__(
        self,
        persist_directory: str,
        collection_name: str,
        embedding_function=None
    ):
        """
        Initialize a persistent ChromaDB client and create a collection.
        
        :param persist_directory: Directory to store persistent data
        :param collection_name: Name of the collection to be created and used throughout
        :param embedding_function: Optional custom embedding function
        """
        # Initialize a persistent client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        if embedding_function is None:
            self.__embedding_function = embedding_functions.DefaultEmbeddingFunction()
        self.__embedding_function = embedding_function
        self.__collection_name = collection_name
        # Create or retrieve a collection and store it for reuse
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedding_function
        )

    def add_chunks(
        self,
        data_chunks: list, 
        metadata: list,
        ids: list,
        **kwargs
    ):
        """
        Add data chunks (with metadata) to the collection.
        
        :param data_chunks: List of data chunks (text, vectors, etc.)
        :param metadata: List of dictionaries containing metadata corresponding to each data chunk
        :param ids: List of unique ids for each data chunk
        """
        self.collection.add(
            documents=data_chunks,
            metadatas=metadata,
            ids=ids
        )

    def update_chunks(
        self,
        data_chunks: list,
        metadata: list,
        ids: list,
        **kwargs
    ):
        """
        Update data chunks and metadata in the collection.
        
        :param data_chunks: List of data chunks to update
        :param metadata: List of dictionaries containing updated metadata
        :param ids: List of unique ids corresponding to the data chunks
        """
        self.collection.update(documents=data_chunks, metadatas=metadata, ids=ids)

    def delete_chunks(
        self,
        ids: list,
        **kwargs
    ):
        """
        Delete data chunks from the collection using their ids.
        
        :param ids: List of ids for the data chunks to delete
        """
        self.collection.delete(ids=ids)

    def retrieve_top_k_chunks(
        self,
        text: str,
        k: int,
        **kwargs
    ):
        """
        Retrieve the top k data chunks from the collection based on similarity to the query text.
        
        :param query_embedding: The embedding of the query to search for
        :param k: Number of top results to retrieve
        :return: The top k data chunks and their corresponding metadata
        """

        results = self.collection.query(query_texts=text, n_results=k)
        chunk_list: List[Chunk] = []
        for id, chunk_text in enumerate(results["documents"][0]):
            chunk = Chunk(
                chunk_id=results["ids"][0][id],
                text=chunk_text,
                metadata=results["metadatas"][0][id]
            )
            chunk_list.append(chunk)
        return chunk_list

    def get_client(self):
        """
        Get the underlying ChromaDB client.
        
        :return: The ChromaDB client
        """
        return self.client

    def get_or_create_collection(self):
        """
        Get the underlying collection.
        
        :return: The collection
        """
        return self.client.get_or_create_collection(
            name=self.__collection_name,
            embedding_function=self.__embedding_function
        )
    
    def delete_store(self):
        """
        Delete the entire store.
        """
        self.client.delete_collection(self.collection.name)

    