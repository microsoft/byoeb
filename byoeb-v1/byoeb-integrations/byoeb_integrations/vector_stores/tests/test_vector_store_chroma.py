import os
from typing import List
from byoeb_core.models.vector_stores.chunk import Chunk
from byoeb_integrations.embeddings.llama_index.azure_openai import AzureOpenAIEmbed
from byoeb_integrations.vector_stores.chroma.base import ChromaDBVectorStore
from byoeb_integrations.embeddings.chroma.llama_index_azure_openai import AzureOpenAIEmbeddingFunction
from azure.identity import DefaultAzureCredential, get_bearer_token_provider, AzureCliCredential
from byoeb_integrations.vector_stores.llama_index.llama_index_chroma_store import LlamaIndexChromaDBStore
from byoeb_integrations import test_environment_path
from dotenv import load_dotenv

load_dotenv(test_environment_path)

os.environ["AZURE_ENDPOINT"] = "https://swasthyabot-oai-vision.openai.azure.com/"
AZURE_ENDPOINT = os.getenv('AZURE_ENDPOINT')
AZURE_COGNITIVE_ENDPOINT = os.getenv('AZURE_COGNITIVE_ENDPOINT')
EMBEDDINGS_MODEL=os.getenv('EMBEDDINGS_MODEL')
EMBEDDINGS_ENDPOINT=os.getenv('EMBEDDINGS_ENDPOINT')
EMBEDDINGS_DEPLOYMENT_NAME=os.getenv('EMBEDDINGS_DEPLOYMENT_NAME')
EMBEDDINGS_API_VERSION=os.getenv('EMBEDDINGS_API_VERSION')

def test_chroma_vector_store_ops():
    token_provider = get_bearer_token_provider(
        AzureCliCredential(), AZURE_COGNITIVE_ENDPOINT
    )
    
    embedding_fn = AzureOpenAIEmbeddingFunction(
        model=EMBEDDINGS_MODEL,
        deployment_name=EMBEDDINGS_DEPLOYMENT_NAME,
        azure_endpoint=EMBEDDINGS_ENDPOINT,
        token_provider=token_provider,
        api_version=EMBEDDINGS_API_VERSION
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
        AzureCliCredential(), AZURE_COGNITIVE_ENDPOINT
    )

    azure_openai_embed = AzureOpenAIEmbed(
        model=EMBEDDINGS_MODEL,
        deployment_name=EMBEDDINGS_DEPLOYMENT_NAME,
        azure_endpoint=EMBEDDINGS_ENDPOINT,
        token_provider=token_provider,
        api_version=EMBEDDINGS_API_VERSION
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