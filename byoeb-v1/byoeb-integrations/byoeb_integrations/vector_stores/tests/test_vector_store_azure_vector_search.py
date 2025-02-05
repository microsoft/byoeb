import os
import hashlib
import asyncio
from datetime import datetime
from azure.identity import DefaultAzureCredential, AzureCliCredential, get_bearer_token_provider
from byoeb_integrations.embeddings.llama_index.azure_openai import AzureOpenAIEmbed
from byoeb_integrations.llms.llama_index.llama_index_azure_openai import AsyncLLamaIndexAzureOpenAILLM
from byoeb_integrations import test_environment_path
from dotenv import load_dotenv
from byoeb_integrations.vector_stores.azure_vector_search.azure_vector_search import AzureVectorStore, AzureVectorSearchType

load_dotenv(test_environment_path)

# Azure Search Config
SERVICE_NAME = "byoeb-search"
INDEX_NAME = "byoeb_index"
ENDPOINT = f"https://{SERVICE_NAME}.search.windows.net"

AZURE_COGNITIVE_ENDPOINT = os.getenv('AZURE_COGNITIVE_ENDPOINT')
EMBEDDINGS_MODEL=os.getenv('EMBEDDINGS_MODEL')
EMBEDDINGS_ENDPOINT=os.getenv('EMBEDDINGS_ENDPOINT')
EMBEDDINGS_DEPLOYMENT_NAME=os.getenv('EMBEDDINGS_DEPLOYMENT_NAME')
EMBEDDINGS_API_VERSION=os.getenv('EMBEDDINGS_API_VERSION')

AZURE_COGNITIVE_ENDPOINT = os.getenv('AZURE_COGNITIVE_ENDPOINT')
LLM_MODEL = os.getenv('LLM_MODEL')
LLM_ENDPOINT = os.getenv('LLM_ENDPOINT')
LLM_API_VERSION = os.getenv('LLM_API_VERSION')
token_provider = get_bearer_token_provider(
    AzureCliCredential(), AZURE_COGNITIVE_ENDPOINT
)

token_provider = get_bearer_token_provider(
    AzureCliCredential(), AZURE_COGNITIVE_ENDPOINT
)
embedding_fn = AzureOpenAIEmbed(
    model=EMBEDDINGS_MODEL,
    deployment_name=EMBEDDINGS_DEPLOYMENT_NAME,
    api_version=EMBEDDINGS_API_VERSION,
    azure_endpoint=EMBEDDINGS_ENDPOINT,
    token_provider=token_provider,
).get_embedding_function()

llama_index_azure_openai = AsyncLLamaIndexAzureOpenAILLM(
    model=LLM_MODEL,
    deployment_name=LLM_MODEL,
    azure_endpoint=LLM_ENDPOINT,
    token_provider=token_provider,
    api_version=LLM_API_VERSION
)

texts = [
    "Photosynthesis is the process by which green plants convert sunlight into chemical energy, producing oxygen and glucose.",
    "Chlorophyll, the green pigment in plants, absorbs light energy from the sun to drive photosynthesis.",
    "The two main stages of photosynthesis are the light-dependent reactions and the Calvin cycle.",
    "During the light-dependent reactions, sunlight is used to split water molecules, releasing oxygen and storing energy in ATP and NADPH.",
    "The Calvin cycle, also called the light-independent reaction, uses ATP and NADPH to convert carbon dioxide into glucose.",
    "Plants take in carbon dioxide through tiny openings called stomata and release oxygen as a byproduct of photosynthesis.",
    "Photosynthesis occurs in the chloroplasts, organelles found in plant cells that contain chlorophyll.",
    "Without photosynthesis, life on Earth would not exist as it provides oxygen and food for most living organisms.",
    "The equation for photosynthesis is: 6CO2 + 6H2O + light energy → C6H12O6 + 6O2.",
    "Photosynthesis is essential for maintaining atmospheric oxygen levels and reducing carbon dioxide in the environment.",
    "Algae and some bacteria, like cyanobacteria, also perform photosynthesis, contributing to global oxygen production.",
    "The rate of photosynthesis is influenced by factors such as light intensity, temperature, and carbon dioxide concentration.",
    "In desert plants, CAM photosynthesis allows them to conserve water by absorbing CO2 at night.",
    "C4 photosynthesis, used by crops like corn and sugarcane, improves efficiency in hot climates.",
    "Artificial photosynthesis is being studied to create clean energy by mimicking natural processes.",
    "The oxygen produced during photosynthesis supports aerobic respiration in animals and humans.",
    "Photosynthesis evolved over 2.5 billion years ago, leading to the Great Oxygenation Event.",
    "The process of photosynthesis plays a crucial role in the carbon cycle, recycling carbon between organisms and the atmosphere.",
    "Scientists study photosynthesis to improve crop yields and develop sustainable energy solutions.",
    "Deforestation and pollution negatively impact photosynthesis by reducing plant populations and increasing greenhouse gases."
]

languages_translation_prompts = {
    "hi": "You are an english to hindi translator.",
}
async def test_azure_vector_search_upload_documents():
    
    ids = [hashlib.md5(text.encode()).hexdigest() for text in texts]
    metadatas = [
        {
            "source": str(i),
            "creation_timestamp": str(int(datetime.now().timestamp())),
            "update_timestamp": str(int(datetime.now().timestamp())),
        }
        for i in range(len(texts))
    ]

    azure_vector_search = AzureVectorStore(
        SERVICE_NAME,
        INDEX_NAME,
        embedding_fn,
        credential=DefaultAzureCredential()
    )
    await azure_vector_search.aadd_chunks(
        ids=ids,
        data_chunks=texts,
        metadata=metadatas,
        llm_client=llama_index_azure_openai,
        languages_translation_prompts=languages_translation_prompts,
        show_progress=True
    )

async def test_azure_vector_search_query():

    query_texts = [
        "What is photosynthesis?",
        "Explain chlorophyll",
        "What is photosynthesis?",
        "Explain chlorophyll"
    ]
    azure_vector_search = AzureVectorStore(
        SERVICE_NAME,
        INDEX_NAME,
        embedding_fn,
        credential=DefaultAzureCredential()
    )
    for query_text in query_texts:
        start_time = datetime.now().timestamp()
        results = await azure_vector_search.aretrieve_top_k_chunks(
            query_text=query_text,
            k=3,
            search_type=AzureVectorSearchType.DENSE.value,
            select=["id", "text", "metadata", "related_questions"],
            vector_field="text_vector_3072"
        )
        print("Results: ", results)
        end_time = datetime.now().timestamp()
        print("Execution Time: ", end_time - start_time)

def test_azure_vector_search_delete():
    azure_vector_search = AzureVectorStore(
        SERVICE_NAME,
        INDEX_NAME,
        embedding_fn,
        credential=DefaultAzureCredential()
    )
    azure_vector_search.delete_store()

if __name__ == "__main__":
    # asyncio.run(test_azure_vector_search_upload_documents())
    asyncio.run(test_azure_vector_search_query())
    # test_azure_vector_search_delete()
    

