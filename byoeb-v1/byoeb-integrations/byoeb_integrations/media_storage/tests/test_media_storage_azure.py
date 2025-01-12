import json
import pytest
import asyncio
import os
from pydub import AudioSegment
from pydub.generators import Sine
from byoeb_integrations.media_storage.azure.async_azure_blob_storage import AsyncAzureBlobStorage
from byoeb_core.media_storage.base import BaseMediaStorage
from byoeb_core.models.media_storage.file_data import FileMetadata, FileData
from azure.identity import DefaultAzureCredential
from byoeb_integrations import test_environment_path
from dotenv import load_dotenv

load_dotenv(test_environment_path)

MEDIA_STORAGE_ACCOUNT_URL=os.getenv("MEDIA_STORAGE_ACCOUNT_URL")
MEDIA_STORAGE_CONTAINER_NAME=os.getenv("MEDIA_STORAGE_CONTAINER_NAME")

@pytest.fixture
def event_loop():
    """Create and provide a new event loop for each test."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

def create_text_sample(file_path: str):
    # Open the file in write mode and add some content
    with open(file_path, "w") as file:
        file.write("Hello, this is a sample text file created with Python!\n")
        file.write("You can add as many lines as you like.\n")
        file.write("Each line will be written to the file.\n")

def create_audio_sample(file_name: str, duration_ms: int = 1000, frequency: int = 440):
    """
    Create an audio sample and save it to a file.
    
    :param file_name: The name of the output audio file.
    :param duration_ms: Duration of the audio sample in milliseconds.
    :param frequency: Frequency of the sine wave (default is 440 Hz, A4 note).
    """
    # Generate a sine wave with the given frequency and duration
    sine_wave = Sine(frequency).to_audio_segment(duration=duration_ms)

    # Export the audio to a file
    sine_wave.export(file_name, format="wav")

async def aazure_blob_storage_audio_ops():
    default_credential = DefaultAzureCredential()
    account_url = MEDIA_STORAGE_ACCOUNT_URL
    container_name = MEDIA_STORAGE_CONTAINER_NAME
    async_azure_blob_storage = AsyncAzureBlobStorage(
        container_name=container_name,
        account_url=account_url,
        credentials=default_credential
    )
    assert (isinstance(async_azure_blob_storage, BaseMediaStorage)) is True
    # Example usage: Create a 1-second, 440Hz sine wave tone and save it to "audio_sample.wav"
    file_name = "audio_hello"
    file_path = "audio_hello.wav"
    create_audio_sample(file_path, duration_ms=1000, frequency=440)
    await async_azure_blob_storage.aupload_file(file_name, file_path)
    status, response = await async_azure_blob_storage.aget_file_properties(file_name)
    if isinstance(response, FileMetadata):
       response=FileMetadata(**response.model_dump())
    status, response = await async_azure_blob_storage.adownload_file(response.file_name)
    if isinstance(response, FileData):
       response=FileData(**response.model_dump())
    await async_azure_blob_storage.adelete_file(file_name)
    assert response is not None
    await async_azure_blob_storage._close()

async def aazure_blob_storage_text_ops():
    default_credential = DefaultAzureCredential()
    account_url = MEDIA_STORAGE_ACCOUNT_URL
    container_name = MEDIA_STORAGE_CONTAINER_NAME
    async_azure_blob_storage = AsyncAzureBlobStorage(
        container_name=container_name,
        account_url=account_url,
        credentials=default_credential
    )
    # files = await async_azure_blob_storage.get_all_files()
    file_name = "test/sample_text"
    file_path = "sample_text.txt"
    create_text_sample(file_path)
    await async_azure_blob_storage.aupload_file(file_name, file_path)
    status, response = await async_azure_blob_storage.aget_file_properties(file_name)
    if isinstance(response, FileMetadata):
       response=FileMetadata(**response.model_dump())
    status, response = await async_azure_blob_storage.adownload_file(response.file_name)
    if isinstance(response, FileData):
       response=FileData(**response.model_dump())
    await async_azure_blob_storage.adelete_file(file_name)
    assert response is not None
    await async_azure_blob_storage._close()

def test_async_azure_blob_storage_text(event_loop):
    event_loop.run_until_complete(aazure_blob_storage_text_ops())

def test_async_azure_blob_storage_audio(event_loop):
    event_loop.run_until_complete(aazure_blob_storage_audio_ops())

if __name__ == "__main__":
    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(aazure_blob_storage_text_ops())
    event_loop.close()