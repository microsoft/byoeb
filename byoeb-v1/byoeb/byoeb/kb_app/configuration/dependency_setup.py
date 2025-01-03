import os
import byoeb.utils.utils as byoeb_utils
from datetime import datetime
from typing import List
from byoeb.kb_app.configuration.config import app_config
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from byoeb_integrations.media_storage.azure.async_azure_blob_storage import AsyncAzureBlobStorage
from byoeb_integrations.embeddings.llama_index.azure_openai import AzureOpenAIEmbed
from byoeb_integrations.vector_stores.llama_index.llama_index_chroma_store import LlamaIndexChromaDBStore

account_url = app_config["media_storage"]["azure"]["account_url"]
container_name = app_config["media_storage"]["azure"]["container_name"]
model = app_config["embeddings"]["azure"]["model"]
deployment_name = app_config["embeddings"]["azure"]["deployment_name"]
aoai_endpoint = app_config["embeddings"]["azure"]["endpoint"]
cognitive_services_endpoint = app_config["app"]["azure_cognitive_endpoint"]
api_version = app_config["embeddings"]["azure"]["api_version"]
default_credential = DefaultAzureCredential()
token_provider = get_bearer_token_provider(default_credential, cognitive_services_endpoint)
collection_name = app_config["vector_store"]["chroma"]["doc_collection_name"]

git_root_dir = byoeb_utils.get_git_root_path()
vector_db_path = os.path.join(git_root_dir, "../vector_db")

azure_openai_embed = AzureOpenAIEmbed(
    model=model,
    deployment_name=deployment_name,
    azure_endpoint=aoai_endpoint,
    token_provider=token_provider,
    api_version=api_version
)

amedia_storage = AsyncAzureBlobStorage(
    container_name=container_name,
    account_url=account_url,
    credentials=default_credential
)

vector_store = LlamaIndexChromaDBStore(
    persist_directory=vector_db_path,
    collection_name=collection_name,
    embedding_function=azure_openai_embed.get_embedding_function()
)