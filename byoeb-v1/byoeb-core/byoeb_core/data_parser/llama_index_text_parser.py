from typing import List
from byoeb_core.models.media_storage.file_data import FileData, FileMetadata
from enum import Enum
from llama_index.core.schema import TextNode, Document
from llama_index.core.text_splitter import SentenceSplitter
from llama_index.core.node_parser import TokenTextSplitter

class LLamaIndexTextSplitterType(Enum):
    SENTENCE = "sentence"
    SEMANTIC_DOUBLE_MERGING = "semantic_double_merging"
    TOKEN_TEXT_SPLITTER = "token_text_splitter"

class LLamaIndexTextParser:
    def __init__(
        self,
        chunk_size: int = 256,
        chunk_overlap: int = 10,
        separator: str = " "
    ):
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._separator = separator

    def get_sentence_splitter(
        self,
    ) -> SentenceSplitter:
        return SentenceSplitter(
            chunk_size=self._chunk_size,
            chunk_overlap=self._chunk_overlap,
            separator=self._separator
        )
    
    def get_token_text_splitter(
        self,
    ) -> TokenTextSplitter:
        return TokenTextSplitter(
            chunk_size=self._chunk_size,
            chunk_overlap=self._chunk_overlap,
            separator=self._separator
        )
    
    def get_splitter(
        self,
        type
    ):
        if type == LLamaIndexTextSplitterType.SENTENCE:
            return self.get_sentence_splitter()
        elif type == LLamaIndexTextSplitterType.TOKEN_TEXT_SPLITTER:
            return self.get_token_text_splitter()
        else:
            raise ValueError("Invalid type")
        
    def get_chunks_from_collection(
        self,
        data: List[str] | List[FileData],
        encoding: str = "utf-8",
        splitter_type=LLamaIndexTextSplitterType.SENTENCE
    ):
        metadatas = []
        texts = data
        if isinstance(texts, list) and all(isinstance(item, FileData) for item in texts):
            texts = [d.data.decode(encoding) for d in data]
            metadatas = [d.metadata.model_dump() for d in data]
        else:
            metadatas = [{} for _ in data]
        documents = [Document(text=text, metadata=metadata) for text, metadata in zip(texts, metadatas)]
        splitter = self.get_splitter(splitter_type)
        nodes = splitter.get_nodes_from_documents(documents)
        return nodes
    
    def get_chunks_from_text(
        self,
        data: str | FileData,
        encoding: str = "utf-8",
        splitter_type=LLamaIndexTextSplitterType.SENTENCE
    ) -> List[TextNode]:
        metadata = {}
        text = data
        if isinstance(data, FileData):
            text = data.data.decode(encoding)
            metadata = data.metadata.model_dump()
        document = Document(
            text=text,
            metadata=metadata
        )
        splitter = self.get_splitter(splitter_type)
        nodes = splitter.get_nodes_from_documents([document])
        return nodes


if __name__ == "__main__":
    text_parser = LLamaIndexTextParser(chunk_size=50, chunk_overlap=1)
    file_data_1 = FileData(
        data=b"This is a test sentence. This is another test sentence.",
        metadata=FileMetadata(
            file_name="abc.txt",
            file_type=".txt",
            creation_time="2021-09-01T00:00:00Z"
        )
    )
    file_data_2 = FileData(
        data=b"How are you doing? I am doing well.",
        metadata=FileMetadata(
            file_name="xyz.txt",
            file_type=".txt",
            creation_time="2021-09-01T00:00:00Z"
        )
    )
    text_1 = "This is a test sentence. This is another test sentence."
    text_2 = "How are you doing? I am doing well."
    chunks = text_parser.get_chunks_from_collection([text_1,text_2])
    print(chunks)
