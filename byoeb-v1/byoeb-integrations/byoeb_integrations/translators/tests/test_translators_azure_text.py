import os
import asyncio
import pytest
import logging
from byoeb_integrations.translators.text.azure.async_azure_text_translator import AsyncAzureTextTranslator
from azure.identity import DefaultAzureCredential
from byoeb_integrations import test_environment_path
from dotenv import load_dotenv

load_dotenv(test_environment_path)

credential = DefaultAzureCredential()
TEXT_TRANSLATOR_RESOURCE_ID=os.getenv('TEXT_TRANSLATOR_RESOURCE_ID')
TEXT_TRANSLATOR_REGION=os.getenv('TEXT_TRANSLATOR_REGION')

@pytest.fixture
def event_loop():
    """Create and provide a new event loop for each test."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

async def aazure_translate_text_en_hi():
    async_azure_text_translator = AsyncAzureTextTranslator(
        credential=credential,
        resource_id=TEXT_TRANSLATOR_RESOURCE_ID,
        region=TEXT_TRANSLATOR_REGION
    )
    input_text = "Hello, how are you?"
    source_language = "en"
    target_language = "hi"
    translated_text = await async_azure_text_translator.atranslate_text(
        input_text=input_text,
        source_language=source_language,
        target_language=target_language
    )
    print(translated_text)
    assert translated_text is not None
    assert translated_text != input_text

async def aazure_translate_text_en_en():
    async_azure_text_translator = AsyncAzureTextTranslator(
        credential=credential,
        resource_id=TEXT_TRANSLATOR_RESOURCE_ID,
        region=TEXT_TRANSLATOR_REGION
    )
    input_text = "Hello, how are you?"
    source_language = "en"
    target_language = "en"
    translated_text = await async_azure_text_translator.atranslate_text(
        input_text=input_text,
        source_language=source_language,
        target_language=target_language
    )
    assert translated_text is not None
    assert translated_text == input_text

# asyncio.run(aazure_translate_text_en_hi())
def test_aazure_translate_text_en_hi(event_loop):
    event_loop.run_until_complete(aazure_translate_text_en_hi())

def test_aazure_translate_text_en_en(event_loop):
    event_loop.run_until_complete(aazure_translate_text_en_en())

if __name__ == "__main__":
    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(aazure_translate_text_en_hi())
    event_loop.close()