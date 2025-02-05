import asyncio
import logging
from byoeb.kb_app.configuration.dependency_setup import (
    amedia_storage,
    vector_store
)
from typing import List
from datetime import datetime
from byoeb_core.data_parser.llama_index_text_parser import LLamaIndexTextParser, LLamaIndexTextSplitterType
from byoeb_core.models.media_storage.file_data import FileMetadata, FileData

logger = logging.getLogger("kb_service")
text_parser = LLamaIndexTextParser(
        chunk_size=300,
        chunk_overlap=50,
    )

async def create_kb_from_blob_store():
    vector_store.delete_store()
    files = await amedia_storage.aget_all_files_properties()
    files_data = await abulk_download_files(files)
    chunks = text_parser.get_chunks_from_collection(
        files_data,
        splitter_type=LLamaIndexTextSplitterType.SENTENCE
    )
    vector_store.add_nodes(chunks)
    collection_count = vector_store.collection.count()
    print(f"Collection count: {collection_count}")
    return collection_count

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
