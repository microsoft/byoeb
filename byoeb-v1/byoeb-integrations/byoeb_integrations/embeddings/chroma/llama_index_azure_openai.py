from typing import Any
from byoeb_integrations.embeddings.llama_index.azure_openai import AzureOpenAIEmbed
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
from chromadb import Documents, EmbeddingFunction, Embeddings

class AzureOpenAIEmbeddingFunction(EmbeddingFunction):
    def __init__(
        self,
        model: str,
        deployment_name: str,
        api_version: str,
        azure_endpoint: str,
        token_provider: Any = None,
        api_key: str = None,
        **kwargs
    ) -> None:
        azure_openai_embed = AzureOpenAIEmbed(
            model=model,
            deployment_name=deployment_name,
            azure_endpoint=azure_endpoint,
            token_provider=token_provider,
            api_version=api_version,
            api_key=api_key,
            reuse_client=False
        )
        self.__embedding_fn = azure_openai_embed.get_embedding_function()

    def __call__(self, input: Documents) -> Embeddings:
        return [self.__embedding_fn.get_text_embedding(doc) for doc in input]