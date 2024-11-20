import os
from azure.identity import DefaultAzureCredential, get_bearer_token_provider, AzureCliCredential
from byoeb_integrations.embeddings.chroma.llama_index_azure_openai import AzureOpenAIEmbeddingFunction
from byoeb_integrations import test_environment_path
from dotenv import load_dotenv

load_dotenv(test_environment_path)

AZURE_COGNITIVE_ENDPOINT = os.getenv('AZURE_COGNITIVE_ENDPOINT')
EMBEDDINGS_MODEL=os.getenv('EMBEDDINGS_MODEL')
EMBEDDINGS_ENDPOINT=os.getenv('EMBEDDINGS_ENDPOINT')
EMBEDDINGS_DEPLOYMENT_NAME=os.getenv('EMBEDDINGS_DEPLOYMENT_NAME')
EMBEDDINGS_API_VERSION=os.getenv('EMBEDDINGS_API_VERSION')

def test_llama_index_azure_openai():
    model="text-embedding-3-large"
    deployment_name="text-embedding-3-large"
    api_version="2023-03-15-preview"
    token_provider = get_bearer_token_provider(
        AzureCliCredential(), AZURE_COGNITIVE_ENDPOINT
    )

    embedding_func = AzureOpenAIEmbeddingFunction(
        model=EMBEDDINGS_MODEL,
        deployment_name=EMBEDDINGS_DEPLOYMENT_NAME,
        azure_endpoint=EMBEDDINGS_ENDPOINT,
        token_provider=token_provider,
        api_version=EMBEDDINGS_API_VERSION
    )

    assert embedding_func.__call__(input = ["This is it"]) is not None
