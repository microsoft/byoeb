import asyncio
import logging
import byoeb_services.singletons as singleton
from byoeb_services.kb_services.delete_kb import delete_kb
from typing import List
from datetime import datetime
from byoeb_core.data_parser.llama_index_text_parser import LLamaIndexTextParser, LLamaIndexTextSplitterType
from byoeb_core.models.media_storage.file_data import FileMetadata, FileData

logger = logging.getLogger("kb_serice")
text_parser = LLamaIndexTextParser(
        chunk_size=300,
        chunk_overlap=50,
    )

async def create_kb():
    files = await singleton.amedia_storage.aget_all_files_properties()
    files_data = await abulk_download_files(files)
    chunks = text_parser.get_chunks_from_collection(
        files_data,
        splitter_type=LLamaIndexTextSplitterType.SENTENCE
    )
    singleton.vector_store.add_nodes(chunks)
    collection_count = singleton.vector_store.collection.count()
    print(f"Collection count: {collection_count}")

async def abulk_download_files(
    all_files: List[FileMetadata]
) -> List[FileData]:
    def create_batches(batch_size=5):
        return [all_files[i:i + batch_size] for i in range(0, len(all_files), batch_size)]
    
    async def get_batch_results(batch):
        tasks = []
        for file in batch:
            task = singleton.amedia_storage.adownload_file(file.file_name)
            tasks.append(task)
        return await asyncio.gather(*tasks)
    
    files_data = []
    batches = create_batches(5)
    for batch in batches:
        batch_results = await get_batch_results(batch)
        for result in batch_results:
            status, response = result
            if status != 200:
                continue
            if isinstance(response, FileData):
                response=FileData(**response.model_dump())
                files_data.append(response)
    return files_data



import byoeb_services.singletons as singleton

def delete_kb():
    singleton.vector_store.delete_store()


from datetime import datetime
from typing import List
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from byoeb_integrations.media_storage.azure.async_azure_blob_storage import AsyncAzureBlobStorage
from byoeb_integrations.embeddings.llama_index.azure_openai import AzureOpenAIEmbed
from byoeb_integrations.vector_stores.llama_index.llama_index_chroma_store import LlamaIndexChromaDBStore

account_url = "https://kgretrieval.blob.core.windows.net"
container_name = "testcontainerbyoeb"
model="text-embedding-3-large"
deployment_name="text-embedding-3-large"
aoai_endpoint = "https://swasthyabot-oai-vision.openai.azure.com/"
cognitive_services_endpoint = "https://cognitiveservices.azure.com/.default"
api_version="2023-03-15-preview"
default_credential = DefaultAzureCredential()
token_provider = get_bearer_token_provider(default_credential, cognitive_services_endpoint)
persistent_directory = "./vdb"
collection_name = "test"

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
    persist_directory=persistent_directory,
    collection_name=collection_name,
    embedding_function=azure_openai_embed.get_embedding_function()
)
