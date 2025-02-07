import os
import asyncio
from tqdm.asyncio import tqdm
from azure.identity import DefaultAzureCredential
from byoeb_integrations.media_storage.azure.async_azure_blob_storage import AsyncAzureBlobStorage
from glob import glob

async def upload_folder_to_blob(media_storage: AsyncAzureBlobStorage, folder_path):
    txt_file_paths = glob(os.path.join(folder_path, "*.txt"))
    async def upload_file(file_path):
        blob_file_name = f"expert_update_documents/{os.path.basename(file_path)}"
        await media_storage.aupload_file(  # Ensure this method exists
            file_path=file_path,
            file_name=blob_file_name
        )

    # Run uploads concurrently for better performance
    await asyncio.gather(*(upload_file(file) for file in tqdm(txt_file_paths, desc="Uploading files")))

async def get_files_in_blob(media_storage: AsyncAzureBlobStorage):
    files = await media_storage.aget_all_files_properties()
    print(files[:5])
    
async def main():
    folder_path = "/home/rash598/rash598_byoeb/byoeb/byoeb-v1/byoeb/byoeb/update_documents"
    account_url = "https://khushibabyashastorage.blob.core.windows.net"
    container_name = "ashacontainer"

    media_storage = AsyncAzureBlobStorage(
        container_name=container_name,
        account_url=account_url,
        credentials=DefaultAzureCredential()
    )
    await upload_folder_to_blob(media_storage, folder_path)
    await media_storage._close()

if __name__ == "__main__":
    asyncio.run(main())

