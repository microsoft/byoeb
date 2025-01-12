from typing import Any
from byoeb_integrations.embeddings.llama_index.openai import OpenAIEmbed
from llama_index.embeddings.openai import OpenAIEmbedding
from chromadb import Documents, EmbeddingFunction, Embeddings


class OpenAIEmbeddingFunction(EmbeddingFunction):
    def __init__(
            self,
            model: str,
            api_endpoint: str,
            api_key: str = None,
            **kwargs
        ) -> None:
            
            open_ai_embed = OpenAIEmbed(
                model=model,
                api_endpoint=api_endpoint,
                api_key=api_key,
                reuse_client=False
            )
            self.__embedding_fn = open_ai_embed.get_embedding_function()

    def __call__(self, input: Documents) -> Embeddings:
        return [self.__embedding_fn.get_text_embedding(doc) for doc in input]