from typing import Any
from llama_index.embeddings.openai import OpenAIEmbedding
from byoeb_core.embeddings.base import BaseEmbedding

class OpenAIEmbed(BaseEmbedding):
    def __init__(
            self,
            model: str,
            api_endpoint: str,
            api_key: str = None,
            **kwargs
        ) -> None:
            embedding_fn = None
            if model is None:
                raise ValueError("model must be provided")
            if api_endpoint is None:
                raise ValueError("api_endpoint must be provided")
            if api_key is None:
                raise ValueError("api_key must be provided")
            embedding_fn = OpenAIEmbedding(
                model=model,
                api_=api_endpoint,
                api_key=api_key,
                reuse_client=False
            )
            
            self.__embedding_fn = embedding_fn

    def get_embedding_function(self):
        return self.__embedding_fn