import byoeb.utils.utils as byoeb_utils
from byoeb.factory import (
    ChannelRegisterFactory,
    ChannelClientFactory,
    QueueProducerFactory,
    MongoDBFactory
)
from byoeb.handler import (
    ChannelRegisterHandler,
    QueueProducerHandler,
    UsersHandler
)
from byoeb.app.configuration.config import app_config
from byoeb.listener.message_consumer import QueueConsumer
from byoeb.services.databases.mongo_db import MongoDBService

SINGLETON = "singleton"

# channel
channel_register_factory = ChannelRegisterFactory()
channel_client_factory = ChannelClientFactory(config=app_config)
channel_register_handler = ChannelRegisterHandler(channel_register_factory)

# mongo db
mongo_db_factory = MongoDBFactory(
    config=app_config,
    scope=SINGLETON
)

mongo_db_service = MongoDBService(
    config=app_config,
    mongo_db_factory=mongo_db_factory
)

# message queue
queue_producer_factory = QueueProducerFactory(
    config=app_config,
    scope = SINGLETON
)
message_producer_handler = QueueProducerHandler(
    config=app_config,
    queue_producer_factory=queue_producer_factory
)
message_consumer = QueueConsumer(
    config=app_config,
    account_url=app_config["message_queue"]["azure"]["account_url"],
    queue_name=app_config["message_queue"]["azure"]["queue_bot"],
    consuemr_type=app_config["app"]["queue_provider"],
    mongo_db_service=mongo_db_service,
    channel_client_factory=channel_client_factory
)

# user handler
users_handler = UsersHandler(
    db_provider=app_config["app"]["db_provider"],
    mongo_db_facory=mongo_db_factory
)

# Text translator
from byoeb_integrations.translators.text.azure.async_azure_text_translator import AsyncAzureTextTranslator
from byoeb_integrations.translators.speech.azure.async_azure_speech_translator import AsyncAzureSpeechTranslator
from azure.identity import get_bearer_token_provider, AzureCliCredential

token_provider = get_bearer_token_provider(
    AzureCliCredential(), app_config["app"]["azure_cognitive_endpoint"]
)
# TODO: factory implementation
text_translator = AsyncAzureTextTranslator(
    credential=AzureCliCredential(),
    region=app_config["translators"]["text"]["azure"]["region"],
    resource_id=app_config["translators"]["text"]["azure"]["resource_id"],
)

# Speech translator
# TODO: factory implementation
speech_translator = AsyncAzureSpeechTranslator(
    token_provider=token_provider,
    region=app_config["translators"]["speech"]["azure"]["region"],
    resource_id=app_config["translators"]["speech"]["azure"]["resource_id"],
)

# vector store
import os
from byoeb_integrations.embeddings.llama_index.azure_openai import AzureOpenAIEmbed
from byoeb_integrations.vector_stores.llama_index.llama_index_chroma_store import LlamaIndexChromaDBStore

git_root_dir = byoeb_utils.get_git_root_path()
vector_db_path = os.path.join(git_root_dir, "../vector_db")

azure_openai_embed = AzureOpenAIEmbed(
    model=app_config["embeddings"]["azure"]["model"],
    deployment_name=app_config["embeddings"]["azure"]["deployment_name"],
    azure_endpoint=app_config["embeddings"]["azure"]["endpoint"],
    token_provider=token_provider,
    api_version=app_config["embeddings"]["azure"]["api_version"]
)
embedding_fn = azure_openai_embed.get_embedding_function()

vector_store = LlamaIndexChromaDBStore(
    vector_db_path,
    app_config["vector_store"]["chroma"]["collection_name"],
    embedding_function=embedding_fn
)

# llm
from byoeb_integrations.llms.llama_index.llama_index_azure_openai import AsyncLLamaIndexAzureOpenAILLM
llm_client = AsyncLLamaIndexAzureOpenAILLM(
    model=app_config["llms"]["azure"]["model"],
    deployment_name=app_config["llms"]["azure"]["deployment_name"],
    azure_endpoint=app_config["llms"]["azure"]["endpoint"],
    token_provider=token_provider,
    api_version=app_config["llms"]["azure"]["api_version"]
)

# Process user message Chain of Responsibility
from byoeb.services.chat.message_handlers import (
    ByoebUserProcess,
    ByoebUserGenerateResponse, 
    ByoebUserSendResponse
)
byoeb_user_send_response = ByoebUserSendResponse(mongo_db_service=mongo_db_service)
byoeb_user_generate_response = ByoebUserGenerateResponse(successor=byoeb_user_send_response)
byoeb_user_process = ByoebUserProcess(successor=byoeb_user_generate_response)

# Process expert message Chain of Responsibility
from byoeb.services.chat.message_handlers import (
    ByoebExpertProcess,
    ByoebExpertGenerateResponse, 
    ByoebExpertSendResponse
)
byoeb_expert_send_response = ByoebExpertSendResponse(mongo_db_service=mongo_db_service)
byoeb_expert_generate_response = ByoebExpertGenerateResponse(successor=byoeb_expert_send_response)
byoeb_expert_process = ByoebExpertProcess(successor=byoeb_expert_generate_response)