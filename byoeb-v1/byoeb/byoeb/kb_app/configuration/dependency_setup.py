import byoeb.kb_app.configuration.config as env_config
from byoeb.kb_app.configuration.config import app_config
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from byoeb_integrations.media_storage.azure.async_azure_blob_storage import AsyncAzureBlobStorage
from byoeb_integrations.embeddings.llama_index.azure_openai import AzureOpenAIEmbed
from byoeb_integrations.vector_stores.azure_vector_search.azure_vector_search import AzureVectorStore
from byoeb_integrations.llms.llama_index.llama_index_openai import AsyncLLamaIndexOpenAILLM

account_url = app_config["media_storage"]["azure"]["account_url"]
container_name = app_config["media_storage"]["azure"]["container_name"]
model = app_config["embeddings"]["azure"]["model"]
deployment_name = app_config["embeddings"]["azure"]["deployment_name"]
aoai_endpoint = app_config["embeddings"]["azure"]["endpoint"]
cognitive_services_endpoint = app_config["app"]["azure_cognitive_endpoint"]
api_version = app_config["embeddings"]["azure"]["api_version"]
default_credential = DefaultAzureCredential()
token_provider = get_bearer_token_provider(default_credential, cognitive_services_endpoint)

azure_search_service_name = app_config["vector_store"]["azure_vector_search"]["service_name"]
azure_search_doc_index_name = app_config["vector_store"]["azure_vector_search"]["doc_index_name"]

llm_client = AsyncLLamaIndexOpenAILLM(
    model=app_config["llms"]["openai"]["model"],
    api_key=env_config.env_openai_api_key,
    api_version=app_config["llms"]["openai"]["api_version"],
    organization=env_config.env_openai_org_id
)

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

vector_store = AzureVectorStore(
    service_name=azure_search_service_name,
    index_name=azure_search_doc_index_name,
    embedding_function=azure_openai_embed.get_embedding_function(),
    credential=default_credential
)