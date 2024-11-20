import os
from typing import List
from byoeb_core.models.vector_stores.chunk import Chunk
from byoeb_integrations.embeddings.llama_index.azure_openai import AzureOpenAIEmbed
from byoeb_integrations.vector_stores.chroma.base import ChromaDBVectorStore
from byoeb_integrations.embeddings.chroma.llama_index_azure_openai import AzureOpenAIEmbeddingFunction
from azure.identity import DefaultAzureCredential, get_bearer_token_provider, AzureCliCredential
from byoeb_integrations.vector_stores.llama_index.llama_index_chroma_store import LlamaIndexChromaDBStore

os.environ["AZURE_ENDPOINT"] = ""
AZURE_ENDPOINT = os.getenv('AZURE_ENDPOINT')

def test_chroma_vector_store_ops():
    token_provider = get_bearer_token_provider(
        AzureCliCredential(), "https://cognitiveservices.azure.com/.default"
    )

    embedding_fn = AzureOpenAIEmbeddingFunction(
        model="text-embedding-3-large",
        deployment_name="text-embedding-3-large",
        azure_endpoint=AZURE_ENDPOINT,
        token_provider=token_provider,
        api_version="2023-03-15-preview"
    )

    chromavs = ChromaDBVectorStore("./vdb", "test",embedding_function=embedding_fn)
    assert chromavs is not None
    chromavs.add_chunks(["hello", "world"], [{"a": 1}, {"b": 2}], ["1", "2"])
    responses: List[Chunk] = chromavs.retrieve_top_k_chunks("hello", 1)
    assert responses is not None
    for response in responses:
        assert response.text == "hello"
    chromavs.delete_store()

def test_llama_index_chroma_vector_store_ops():
    token_provider = get_bearer_token_provider(
        AzureCliCredential(), "https://cognitiveservices.azure.com/.default"
    )

    azure_openai_embed = AzureOpenAIEmbed(
        model="text-embedding-3-large",
        deployment_name="text-embedding-3-large",
        azure_endpoint=AZURE_ENDPOINT,
        token_provider=token_provider,
        api_version="2023-03-15-preview"
    )
    embedding_fn = azure_openai_embed.get_embedding_function()

    chromavs = LlamaIndexChromaDBStore("./vdb", "test",embedding_function=embedding_fn)
    assert chromavs is not None
    chromavs.add_chunks(["hello", "world"], [{"a": 1}, {"b": 2}], ["1", "2"])
    responses: List[Chunk] = chromavs.retrieve_top_k_chunks("hello", 1)
    assert responses is not None
    for response in responses:
        assert response.text == "hello"
    print(chromavs.collection.count())
    chromavs.delete_store()
    chromavs.add_chunks(["hello", "world"], [{"a": 1}, {"b": 2}], ["1", "2"])
    print(chromavs.collection.count())
    chromavs.delete_store()

if __name__ == "__main__":
    test_llama_index_chroma_vector_store_ops()