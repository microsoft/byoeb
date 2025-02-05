import asyncio
from enum import Enum
from typing import List
from tqdm.asyncio import tqdm
from datetime import datetime
from byoeb_core.vector_stores.base import BaseVectorStore
from byoeb_core.llms.base import BaseLLM
from azure.search.documents import SearchClient, SearchIndexingBufferedSender
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.models import VectorizableTextQuery, IndexAction
from byoeb_core.models.vector_stores.azure.azure_search import AzureSearchNode, Metadata
from byoeb_integrations.vector_stores.related_questions import aget_related_questions
from byoeb_core.models.vector_stores.chunk import Chunk, Chunk_metadata

class AzureVectorSearchType(Enum):
    BM25 = "bm25"
    DENSE = "dense"
    HYBRID = "hybrid"

class AzureVectorStore(BaseVectorStore):
    def __init__(
        self,
        service_name: str,
        index_name: str,
        embedding_function,
        api_key: str = None,
        credential = None,
    ):
        if not service_name:
            raise ValueError("service_name is required")
        if not index_name:
            raise ValueError("index_name is required")
        if not embedding_function:
            raise ValueError("embedding_function is required")
        if not api_key and not credential:
            raise ValueError("api_key or credential is required")
        if api_key and credential:
            raise ValueError("only one of api_key or credential is required")
        if api_key:
            raise NotImplementedError("api_key is not supported yet")
    
        self.__service_name = service_name
        self.__index_name = index_name
        self.__embedding_function = embedding_function
        self.__credential = credential
        self.__endpoint = f"https://{self.__service_name}.search.windows.net"
        self.search_client = SearchClient(
            endpoint=self.__endpoint,
            index_name=self.__index_name,
            credential=credential
        )
        self.search_index_client = SearchIndexClient(
            endpoint=self.__endpoint,
            credential=credential
        )

    def fails(self, error: IndexAction):
        print("Failed to upload document")
        print(error.additional_properties)

    async def __prepare_azure_node(
        self,
        id,
        chunk,
        metadata,
        llm_client: BaseLLM,
        languages_translation_prompts: dict,
        system_prompt
    ) -> AzureSearchNode:
        related_questions = None
        if llm_client is not None:
            related_questions = await aget_related_questions(
                chunk,
                llm_client,
                languages_translation_prompts,
                system_prompt,
            )
        azure_doc = AzureSearchNode(
            id=id,
            text=chunk,
            metadata=Metadata(
                source=metadata["source"],
                creation_timestamp=metadata["creation_timestamp"],
                update_timestamp=metadata["update_timestamp"],
            ),
            text_vector_3072=await self.__embedding_function.aget_text_embedding(chunk),
            related_questions=related_questions,
        )
        return azure_doc
    
    def add_chunks(
        self,
        data_chunks: list, 
        metadata: list,
        ids: list = None,
        **kwargs
    ):
        raise NotImplementedError

    async def aadd_chunks(
        self,
        data_chunks,
        metadata,
        ids,
        llm_client: BaseLLM =None,
        languages_translation_prompts: dict = None,
        system_prompt = None,
        batch_size = 10,
        show_progress=False
    ):
        documents = []
        if languages_translation_prompts is not None and llm_client is None:
            raise ValueError("llm_client is required when languages are provided")
        
        total_batches = (len(data_chunks) + batch_size - 1) // batch_size  # Calculate total batches
    
        # Initialize tqdm progress bar if enabled
        progress_bar = tqdm(total=total_batches, desc="Preparing documents to upload to azure vector search", disable=not show_progress)
        for i in range(0, len(data_chunks), batch_size):
            batch_chunks = data_chunks[i:i+batch_size]
            batch_ids = ids[i:i+batch_size]
            batch_metadata = metadata[i:i+batch_size]

            # Process batch concurrently
            batch_nodes = await asyncio.gather(*[
                self.__prepare_azure_node(
                    id=batch_ids[idx],
                    chunk=batch_chunks[idx],
                    metadata=batch_metadata[idx],
                    llm_client=llm_client,
                    languages_translation_prompts=languages_translation_prompts,
                    system_prompt=system_prompt
                ) for idx in range(len(batch_chunks))
            ])

            # Convert models and extend document list
            documents.extend([node.model_dump(exclude_none=True, exclude_defaults=True) for node in batch_nodes])
            progress_bar.update(1)
        
        progress_bar.close()

        # Upload documents to Azure
        print("Started uploading documents to Azure vector search")
        with SearchIndexingBufferedSender(
            endpoint=self.__endpoint,
            index_name=self.__index_name,
            credential=self.__credential,
            on_error=self.fails
        ) as batch_client:
            batch_client.upload_documents(documents=documents)
        print(f"Uploading process complete")
        # return True

    def update_chunks(
        self,
        data_chunks: list,
        metadata: list,
        ids: list,
        **kwargs
    ):
        raise NotImplementedError
    
    def delete_chunks(
        self,
        ids: list,
        **kwargs
    ):
        raise NotImplementedError

    def retrieve_top_k_chunks(
        self,
        text: str,
        k: int,
        **kwargs
    ):
        raise NotImplementedError
    
    async def aretrieve_top_k_chunks(
        self,
        query_text: str,
        k: int,
        search_type=AzureVectorSearchType.HYBRID.value,
        select=None,
        vector_field=None,
        **kwargs
    ):
        chunk_list: List[Chunk] = []
        results = []
        if (search_type == AzureVectorSearchType.HYBRID or search_type == AzureVectorSearchType.DENSE) and vector_field is None:
            raise ValueError("vector_field is required for dense and hybrid search types")
        if search_type == AzureVectorSearchType.BM25.value:
            results = self.search_client.search(
                search_text=query_text,
                select=select,
                top=k
            )
        elif search_type == AzureVectorSearchType.DENSE.value:
            vector_query = VectorizableTextQuery(
                text=query_text,
                k_nearest_neighbors=10,
                fields=vector_field
            )
            results = self.search_client.search(
                vector_queries=[vector_query],
                select=select,
                top=k
            )
        elif search_type == AzureVectorSearchType.HYBRID.value:
            vector_query = VectorizableTextQuery(
                text=query_text,
                k_nearest_neighbors=10,
                fields=vector_field
            )
            results = self.search_client.search(
                search_text=query_text,
                vector_queries=[vector_query],
                select=select,
                top=k
            )
        else:
            raise ValueError("Invalid search type")

        for result in results:
            azure_search_result = AzureSearchNode(**result)
            chunk = Chunk(
                chunk_id=azure_search_result.id,
                text=azure_search_result.text,
                metadata=Chunk_metadata(
                    source=azure_search_result.metadata.source,
                    creation_timestamp=azure_search_result.metadata.creation_timestamp,
                    update_timestamp=azure_search_result.metadata.update_timestamp
                ),
                related_questions=azure_search_result.related_questions
            )
            chunk_list.append(chunk)
        return chunk_list

    def delete_store(self):
        self.search_index_client.delete_index(self.__index_name)
    
# print("Model: ", EMBEDDINGS_MODEL)
# token_provider = get_bearer_token_provider(
#     AzureCliCredential(), AZURE_COGNITIVE_ENDPOINT
# )
# embedding_fn = AzureOpenAIEmbed(
#     model=EMBEDDINGS_MODEL,
#     deployment_name=EMBEDDINGS_DEPLOYMENT_NAME,
#     api_version=EMBEDDINGS_API_VERSION,
#     azure_endpoint=EMBEDDINGS_ENDPOINT,
#     token_provider=token_provider,
# ).get_embedding_function()

# texts = [
#     "Photosynthesis is the process by which green plants convert sunlight into chemical energy, producing oxygen and glucose.",
#     "Chlorophyll, the green pigment in plants, absorbs light energy from the sun to drive photosynthesis.",
#     "The two main stages of photosynthesis are the light-dependent reactions and the Calvin cycle.",
#     "During the light-dependent reactions, sunlight is used to split water molecules, releasing oxygen and storing energy in ATP and NADPH.",
#     "The Calvin cycle, also called the light-independent reaction, uses ATP and NADPH to convert carbon dioxide into glucose.",
#     "Plants take in carbon dioxide through tiny openings called stomata and release oxygen as a byproduct of photosynthesis.",
#     "Photosynthesis occurs in the chloroplasts, organelles found in plant cells that contain chlorophyll.",
#     "Without photosynthesis, life on Earth would not exist as it provides oxygen and food for most living organisms.",
#     "The equation for photosynthesis is: 6CO2 + 6H2O + light energy → C6H12O6 + 6O2.",
#     "Photosynthesis is essential for maintaining atmospheric oxygen levels and reducing carbon dioxide in the environment.",
#     "Algae and some bacteria, like cyanobacteria, also perform photosynthesis, contributing to global oxygen production.",
#     "The rate of photosynthesis is influenced by factors such as light intensity, temperature, and carbon dioxide concentration.",
#     "In desert plants, CAM photosynthesis allows them to conserve water by absorbing CO2 at night.",
#     "C4 photosynthesis, used by crops like corn and sugarcane, improves efficiency in hot climates.",
#     "Artificial photosynthesis is being studied to create clean energy by mimicking natural processes.",
#     "The oxygen produced during photosynthesis supports aerobic respiration in animals and humans.",
#     "Photosynthesis evolved over 2.5 billion years ago, leading to the Great Oxygenation Event.",
#     "The process of photosynthesis plays a crucial role in the carbon cycle, recycling carbon between organisms and the atmosphere.",
#     "Scientists study photosynthesis to improve crop yields and develop sustainable energy solutions.",
#     "Deforestation and pollution negatively impact photosynthesis by reducing plant populations and increasing greenhouse gases."
# ]

# def upload_documents(documents):
#     # Initialize Search Client
#     credential = DefaultAzureCredential()
#     # search_client = SearchClient(endpoint=ENDPOINT, index_name=INDEX_NAME, credential=credential)
#     documents = [
#         {
#             "id": str(i + 1),
#             "text": chunk,  # Azure will generate embeddings for this
#             "metadata": {"source": f"document_{i + 1}"},
#             "text_vector": embedding_fn.get_text_embedding(chunk)
#         }
#         for i, chunk in enumerate(texts)
#     ]
#     print("Embeddings done")
#     with SearchIndexingBufferedSender(  
#         endpoint=ENDPOINT,  
#         index_name=INDEX_NAME,  
#         credential=credential,  
#     ) as batch_client:  
#         # Add upload actions for all documents  
#         batch_client.upload_documents(documents=documents)
#     # search_client.upload_documents(documents)
#     print(f"Uploaded {len(documents)} documents in total")  

# def bm25_search(
#     search_client: SearchClient,
#     query_text,
#     top_k,
#     select=None,
# ):
#     results = search_client.search(
#         search_text=query_text,
#         top=top_k,
#         select=select
#     )
#     return results

# def dense_search(
#     search_client: SearchClient,
#     query_text,
#     top_k,
#     vector_field,
#     select=None,
# ):
#     vector_query = VectorizableTextQuery(text=query_text, k_nearest_neighbors=10, fields=vector_field)
#     results = search_client.search(
#         search_text=query_text,
#         vector_queries=[vector_query],
#         select=select,
#         top=top_k
#     )
#     return results

# def hybrid_search(
#         search_client: SearchClient,
#         query_text,
#         top_k,
#         vector_field,
#         select=None,
#     ):
#     # Initialize Search Client
#     vector_query = VectorizableTextQuery(
#         text=query_text,
#         k_nearest_neighbors=10,
#         fields=vector_field
#     )
  
#     results = search_client.search(  
#         search_text=query_text,
#         vector_queries= [vector_query],
#         select=select,
#         top=top_k
#     )
#     return results

# credential = DefaultAzureCredential()
# search_client = SearchClient(endpoint=ENDPOINT, index_name=INDEX_NAME, credential=credential)
# query_texts = [
#     "What is photosynthesis?",
#     "Explain chlorophyll",
#     "What is photosynthesis?",
#     "Explain chlorophyll"]

# for query_text in query_texts:
#     start_time = datetime.now().timestamp()
#     search_results = hybrid_search(
#         search_client,
#         query_text,
#         5,
#         vector_field="text_vector",
#         select=["id", "text", "metadata"])
#     for result in search_results:
#         print(result["id"], result["text"])
#     print("Time taken: ", datetime.now().timestamp() - start_time)
# result = search_client.upload_documents(documents)
# print(result)
# print("Documents uploaded successfully!")

# Function to Generate Embeddings
# def get_embedding(text):
#     response = openai.embeddings.create(input=text, model="your-openai-embedding-model")
#     return response["data"][0]["embedding"]

# # Upload Chunks
# documents = []
# for idx, chunk in enumerate(chunks):
#     doc = {
#         "id": f"doc-{idx}",
#         "text": chunk,
#         "metadata": {"source": "document_name", "timestamp": "2025-01-31"},
#         "embedding": Vector(value=get_embedding(chunk), dimension=1536),  # Adjust dimension
#     }
#     documents.append(doc)

# # Push to Azure
# search_client.upload_documents(documents)
# print("Documents uploaded successfully!")

# query_text = "How do plants produce oxygen?"
# search_results = search_client.search(
#     search_text=query_text,
#     query_type=QueryType.SEMANTIC,
#     top=5
# )

# for result in search_results:
#     print(result["text"])

# results = search_client.search(search_text="*", top=10, semantic_configuration_name='S1')
