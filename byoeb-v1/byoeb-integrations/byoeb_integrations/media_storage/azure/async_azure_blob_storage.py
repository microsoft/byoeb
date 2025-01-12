import asyncio
import os
import logging
from typing import Any, List
from byoeb_core.media_storage.base import BaseMediaStorage
from byoeb_core.models.media_storage.file_data import FileMetadata, FileData
from azure.storage.blob.aio import BlobServiceClient
from azure.core.exceptions import (
    ResourceNotFoundError,
    ResourceExistsError,
    ClientAuthenticationError,
    HttpResponseError
)

class StatusCodes:
    OK = 200
    CREATED = 201
    NO_CONTENT = 204
    NOT_FOUND = 404
    CONFLICT = 409
    UNAUTHORIZED = 401
    INTERNAL_SERVER_ERROR = 500

class AsyncAzureBlobStorage(BaseMediaStorage):
    def __init__(
        self,
        container_name: str,
        account_url: str,
        credentials: None,
        connection_string: str = None,
        **kwargs
    ):
        self.__logger = logging.getLogger(self.__class__.__name__)
        if container_name is None:
            raise ValueError("container_name must be provided")
        if credentials is not None and account_url is not None:
            self.__blob_service_client = BlobServiceClient(
                account_url=account_url,
                container_name=container_name,
                credential=credentials
            )
        elif connection_string is not None:
            self.__blob_service_client = BlobServiceClient.from_connection_string(
                connection_string=connection_string,
                container_name=container_name
            )
        else:
            raise ValueError("Either account url and credentials or connection_string must be provided")
        self.__container_name = container_name
    
    async def aget_file_properties(
        self,
        file_name,
    ) -> (str, FileMetadata | str):
        blob_client = self.__blob_service_client.get_blob_client(
            container=self.__container_name,
            blob=file_name
        )
        try:
            properties = await blob_client.get_blob_properties()
            return StatusCodes.OK, FileMetadata(
                file_name=file_name,
                file_type=properties.metadata.get("file_type"),
                creation_time=properties.creation_time.strftime("%Y-%m-%d %H:%M:%S"),
            )
        except ResourceNotFoundError as e:
            self.__logger.error("Blob not found: %s", e)
            return StatusCodes.NOT_FOUND, e.message 
        except Exception as e:
            self.__logger.error("Error getting blob properties: %s", e)
            raise e
        
    async def aget_all_files_properties(
        self,
    ) -> List[FileMetadata]:
        container_name = self.__container_name
        container_client = self.__blob_service_client.get_container_client(container_name)
        files = []
        async for blob in container_client.list_blobs():
            status, properties = await self.aget_file_properties(blob.name)
            if isinstance(properties, FileMetadata):
                files.append(properties)
        return files
    
    async def aupload_file(
        self,
        file_name,
        file_path,
        file_type=None,
    ):
        blob_client = self.__blob_service_client.get_blob_client(
            container=self.__container_name,
            blob=file_name
        )
        if file_type is None:
            file_type = os.path.splitext(file_path)[1]
        metadata = {
            "file_name": file_name,
            "file_type": file_type,
        }
        try:
            with open(file_path, "rb") as data:
                await blob_client.upload_blob(data, metadata=metadata)
            return StatusCodes.CREATED, None
        except ResourceExistsError as e:
            self.__logger.error("Blob already exists: %s", e)
            return StatusCodes.CONFLICT, e.message
        except Exception as e:
            self.__logger.error("Error uploading audio file to blob storage: %s", e)
            raise e
        
    async def adownload_file(
        self,
        file_name,
    ) -> (str, FileData | str):
        blob_client = self.__blob_service_client.get_blob_client(
            container=self.__container_name,
            blob=file_name
        )
        blob_download_reponse = None
        try:
            blob_download_reponse = await blob_client.download_blob()
            properties = await blob_client.get_blob_properties()
            return StatusCodes.OK, FileData(
                data=await blob_download_reponse.readall(),
                metadata=FileMetadata(
                    file_name=file_name,
                    file_type=properties.metadata.get("file_type"),
                    creation_time=properties.creation_time.strftime("%Y-%m-%d %H:%M:%S"),
                )
            )
        except ResourceNotFoundError as e:
            self.__logger.error("Blob not found: %s", e)
            return StatusCodes.NOT_FOUND, e.message
        except Exception as e:
            self.__logger.error("Error downloading audio file from blob storage: %s", e)
            raise e
    
    async def adelete_file(
        self,
        file_name: str,
    ) -> Any:
        blob_client = self.__blob_service_client.get_blob_client(
            container=self.__container_name,
            blob=file_name
        )
        try:
            await blob_client.delete_blob()
        except Exception as e:
            self.__logger.error("Error deleting blob from blob storage: %s", e)
            raise e
    
    def get_blob_service_client(self):
        return self.__blob_service_client
    
    def get_container_name(self):
        return self.__container_name
    
    def get_blob_clinet(
        self,
        blob_name: str
    ):
        return self.__blob_service_client.get_blob_client(
            container=self.__container_name,
            blob=blob_name
        )
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.__blob_service_client.__aexit__(exc_type, exc_val, exc_tb)
        self.__logger.info("Container %s closed", self.__container_name)

    async def _close(self):
        await self.__blob_service_client.close()
        self.__blob_service_client = None
        self.__logger.info("Container %s closed", self.__container_name)
    
    # def __del__(self):
    #     loop = asyncio.get_event_loop()
    #     if loop.is_running():
    #         # If the loop is running, create a future and wait for it
    #         asyncio.ensure_future(
    #             self.__blob_service_client.close(),
    #             loop=loop
    #         ).__await__()
    #     else:
    #         # If no loop is running, use asyncio.run
    #         asyncio.run(self.__blob_service_client.close())
    #     self.__logger.info("Container %s closed", self.__container_name)
    