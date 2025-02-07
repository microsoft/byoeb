import asyncio
import logging
import hashlib
from byoeb.kb_app.configuration.config import prompt_config
from byoeb.kb_app.configuration.dependency_setup import (
    amedia_storage,
    vector_store,
    llm_client
)
from typing import List
from datetime import datetime
from byoeb_core.data_parser.llama_index_text_parser import LLamaIndexTextParser, LLamaIndexTextSplitterType
from byoeb_core.models.media_storage.file_data import FileMetadata, FileData

logger = logging.getLogger("kb_service")


prefix_raw_documents = "raw_documents"
prefix_updated_documents = "expert_update_documents"

async def create_update_files_chunk(files: list):
    delimiter = "##"
    metadatas, texts = [], []
    files = [file for file in files if prefix_updated_documents in file.file_name]
    files_data = await abulk_download_files(files)
    if isinstance(texts, list) and all(isinstance(item, FileData) for item in texts):
        texts = [d.data.decode("utf-8") for d in files_data]
        metadatas = [d.metadata.model_dump() for d in files_data]
    else:
        raise ValueError("Invalid data")
    
    chunk_ids, chunk_texts, chunk_metadatas = [], [], []
    for text, metadata in zip(texts, metadatas):
        sections = [section.strip() for section in text.split(delimiter) if section.strip()]
        for section in sections:
            chunk_id = hashlib.md5(section.encode()).hexdigest()
            chunk_text = section
            chunk_metadata = {
                "source": metadata["file_name"],
                "creation_timestamp": str(int(datetime.now().timestamp())),
                "update_timestamp": str(int(datetime.now().timestamp())),
            }
            chunk_ids.append(chunk_id)
            chunk_texts.append(chunk_text)
            chunk_metadatas.append(chunk_metadata)
    return chunk_ids, chunk_texts, chunk_metadatas

async def create_raw_files_chunks(files: list):
    files = [file for file in files if prefix_raw_documents in file.file_name]
    files_data = await abulk_download_files(files)
    text_parser = LLamaIndexTextParser(
        chunk_size=300,
        chunk_overlap=50,
    )
    chunks = text_parser.get_chunks_from_collection(
        files_data,
        splitter_type=LLamaIndexTextSplitterType.SENTENCE
    )
    chunk_texts = [chunk.text for chunk in chunks]
    chunk_metadatas = [
        {
            "source": chunk.metadata["file_name"],
            "creation_timestamp": str(int(datetime.now().timestamp())),
            "update_timestamp": str(int(datetime.now().timestamp())),
        }
        for chunk in chunks
    ]
    chunk_ids = [hashlib.md5(chunk.text.encode()).hexdigest() for chunk in chunks]
    return chunk_ids, chunk_texts, chunk_metadatas

async def create_kb_from_blob_store():
    files = await amedia_storage.aget_all_files_properties()
    raw_chunks_ids, raw_chunks_text, raw_chunks_metadata = await create_raw_files_chunks(files)
    update_chunks_ids, update_chunks_text, update_chunks_metadata = await create_update_files_chunk(files)
    chunk_ids = raw_chunks_ids + update_chunks_ids
    chunk_texts = raw_chunks_text + update_chunks_text
    chunk_metadatas = raw_chunks_metadata + update_chunks_metadata
    await vector_store.aadd_chunks(
        ids=chunk_ids,
        data_chunks=chunk_texts,
        metadata=chunk_metadatas,
        llm_client=llm_client,
        languages_translation_prompts=prompt_config["languages_translation_prompts"],
        batch_size=10,
        show_progress=True
    )

async def abulk_download_files(
    all_files: List[FileMetadata]
) -> List[FileData]:
    def create_batches(batch_size=5):
        return [all_files[i:i + batch_size] for i in range(0, len(all_files), batch_size)]
    
    async def get_batch_results(batch):
        tasks = []
        for file in batch:
            task = amedia_storage.adownload_file(file.file_name)
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

def delete_kb():
    vector_store.delete_store()

async def main():
    await create_kb_from_blob_store()
    await amedia_storage._close()

if __name__ == "__main__":
    asyncio.run(main())
