import os
from azure.identity import DefaultAzureCredential, get_bearer_token_provider, AzureCliCredential
from byoeb_integrations.embeddings.chroma.llama_index_azure_openai import AzureOpenAIEmbeddingFunction

os.environ["AZURE_ENDPOINT"] = ""
AZURE_ENDPOINT = os.getenv('AZURE_ENDPOINT')

def test_llama_index_azure_openai():
    model="text-embedding-3-large"
    deployment_name="text-embedding-3-large"
    api_version="2023-03-15-preview"
    token_provider = get_bearer_token_provider(
        AzureCliCredential(), ""
    )

    embedding_func = AzureOpenAIEmbeddingFunction(
        model=model,
        deployment_name=deployment_name,
        azure_endpoint=AZURE_ENDPOINT,
        token_provider=token_provider,
        api_version=api_version
    )

    assert embedding_func.__call__(input = ["This is it"]) is not None
