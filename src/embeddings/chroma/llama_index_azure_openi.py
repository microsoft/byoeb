import os
from typing import Any
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
from chromadb import Documents, EmbeddingFunction, Embeddings
from azure.identity import DefaultAzureCredential, get_bearer_token_provider


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
        embedding_fn = None
        if model is None:
            raise ValueError("model must be provided")
        if api_version is None:
            raise ValueError("api_version must be provided")
        if azure_endpoint is None:
            raise ValueError("azure_endpoint must be provided")
        if token_provider is not None:
            embedding_fn = AzureOpenAIEmbedding(
                model=model,
                deployment_name=deployment_name,
                azure_endpoint=azure_endpoint,
                azure_ad_token_provider=token_provider,
                api_version=api_version,
                reuse_client=False
            )
        elif api_key is not None:
            embedding_fn = AzureOpenAIEmbedding(
                model=model,
                deployment_name=deployment_name,
                azure_endpoint=azure_endpoint,
                api_key=api_key,
                api_version=api_version,
                reuse_client=True
            )
        else:
            raise ValueError("Either token_provider or api_key must be provided")
        
        self.__embedding_fn = embedding_fn

    def __call__(self, input: Documents) -> Embeddings:
        return [self.__embedding_fn.get_text_embedding(doc) for doc in input]
    

def get_chroma_llama_index_azure_openai_embeddings_fn() -> AzureOpenAIEmbeddingFunction:
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    )
    return AzureOpenAIEmbeddingFunction(
        model=os.environ["OPENAI_API_EMBED_MODEL"],
        deployment_name=os.environ["OPENAI_API_EMBED_MODEL"],
        azure_endpoint=os.environ["OPENAI_API_EMBED_ENDPOINT"],
        token_provider=token_provider,
        api_version=os.environ["OPENAI_API_EMBED_API_VERSION"]
    )