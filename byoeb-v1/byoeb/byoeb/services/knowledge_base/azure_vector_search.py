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
text_parser = LLamaIndexTextParser(
        chunk_size=300,
        chunk_overlap=50,
    )

async def create_kb_from_blob_store():
    files = await amedia_storage.aget_all_files_properties()
    files_data = await abulk_download_files(files)
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
    await vector_store.aadd_chunks(
        ids=chunk_ids,
        data_chunks=chunk_texts,
        metadata=chunk_metadatas,
        llm_client=llm_client,
        languages_translation_prompts=prompt_config["languages_translation_prompts"],
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
