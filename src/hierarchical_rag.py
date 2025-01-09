from datetime import datetime
import json
from embeddings.chroma.llama_index_azure_openi import get_chroma_llama_index_azure_openai_embeddings_fn
from embeddings.chroma.openai import get_chroma_openai_embedding_fn
from utils import get_client_with_token_provider, get_client_with_key
import os
import chromadb
from chromadb.config import Settings
import yaml

with open("config.yaml") as file:
    config = yaml.load(file, Loader=yaml.FullLoader)

llm_prompts = json.load(open(os.path.join(os.environ["APP_PATH"], os.environ["DATA_PATH"], "llm_prompt.json")))
persist_directory = os.path.join(
    os.path.join(os.environ["APP_PATH"], os.environ["DATA_PATH"]), "vectordb_hierarchy"
)
embedding_fn = get_chroma_openai_embedding_fn()
llm_client = get_client_with_key()
model = os.environ["OPENAI_API_MODEL"].strip()
general = "Generic"

def hierarchical_rag_retrieve(query, org_id):
    chroma_client = chromadb.PersistentClient(
        path=persist_directory, settings=Settings(anonymized_telemetry=False)
    )
    collection = chroma_client.get_collection(
        name=config["PROJECT_NAME"], embedding_function=embedding_fn
    )
    collection_count = collection.count()
    print('collection ids count: ', collection_count)
    relevant_chunks = collection.query(
        query_texts=[query],
        n_results=3,
        where={"org_id": {"$in": [org_id, general]}}
    )
    citations: str = "\n".join(
        [metadata["org_id"] + '-' + metadata["source"] for metadata in relevant_chunks["metadatas"][0]]
    )

    relevant_chunks_string = ""
    relevant_update_chunks_string = ""
    chunks = []

    chunk1 = 0
    chunk2 = 0
    for chunk, chunk_text in enumerate(relevant_chunks["documents"][0]):
        if relevant_chunks["metadatas"][0][chunk]["source"].strip() == "KB Updated":
            relevant_update_chunks_string += (
                f"Chunk #{chunk2 + 1}\n{chunk_text}\n\n"
            )
            chunk2 += 1
            chunks.append((chunk_text, relevant_chunks["metadatas"][0][chunk]["source"].strip(), relevant_chunks["metadatas"][0][chunk]["org_id"].strip()))
        else:
            relevant_chunks_string += f"Chunk #{chunk1 + 1}\n{chunk_text}\n\n"
            chunk1 += 1
            chunks.append((chunk_text, relevant_chunks["metadatas"][0][chunk]["source"].strip(), relevant_chunks["metadatas"][0][chunk]["org_id"].strip()))
    return relevant_chunks_string, relevant_update_chunks_string, citations, chunks

def hierarchical_rag_augment(conversation_history, retrieved_chunks, system_prompt, query):
    query_prompt = f"""
        Today's date is {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\
        
        The following knowledge base chunks have been provided to you as reference:\n\n\
        Raw documents are as follows:\n\
        {retrieved_chunks[0]}\n\n\
        New documents are as follows:\n\
        {retrieved_chunks[1]}\n\n\
        The most recent conversations are here:\n\n\
        {conversation_history}\n\
        You are asked the following query:\n\n\
        "{query}"\n\n\

    """

    prompt = [{"role": "system", "content": system_prompt}]
    prompt.append({"role": "user", "content": query_prompt})
    return prompt

def hierarchical_rag_generate(prompt, schema=None):
    if schema is None:
        response = llm_client.chat.completions.create(
            model=model,
            messages=prompt,
            temperature=0,
        )
        response_text = response.choices[0].message.content.strip()
        return response_text
    
    response = llm_client.chat.completions.create(
        model=model,
        messages=prompt,
        temperature=0,
        response_format= { "type": "json_schema", "json_schema": schema }
    )
    response_text = response.choices[0].message.content.strip()
    return response_text


def rag(query, org_id):
    system_prompt = llm_prompts["answer_query"]
    relevant_chunks_string, relevant_update_chunks_string, citations, chunks = hierarchical_rag_retrieve(query, org_id)
    print(chunks)
    prompt = hierarchical_rag_augment("", (relevant_chunks_string, relevant_update_chunks_string), system_prompt, query)
    response = hierarchical_rag_generate(prompt)
    return response, citations, chunks

# query1 = "What are the list of Health insurance companies that hospital provides ? Share upto 3"
# org_id = "BLR"
# response, citations, chunks = rag(query1, org_id)
# print(response)