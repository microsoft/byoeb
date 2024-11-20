import asyncio
import pytest
import azure.cognitiveservices.speech as speechsdk
from byoeb_integrations.translators.speech.azure.async_azure_speech_translator import AsyncAzureSpeechTranslator
from azure.identity import get_bearer_token_provider, DefaultAzureCredential
from azure.identity import  InteractiveBrowserCredential
# ibc = InteractiveBrowserCredential()
# aadToken = ibc.get_token("https://cognitiveservices.azure.com/.default").token
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
)
# print(aadToken)
resource_id = ""
region=""


# TODO - Add tests for the AsyncAzureSpeechTranslator class using token provider
@pytest.fixture
def event_loop():
    """Create and provide a new event loop for each test."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

async def aazure_bytes_speech_translate_en():
    text = "Hello World !!"
    async_azure_speech_translator = AsyncAzureSpeechTranslator(
        region=region,
        token_provider=token_provider,
        resource_id=resource_id,
    )
    result = await async_azure_speech_translator.atext_to_speech(
        input_text=text,
        source_language="en",
    )
    with open("audio.wav", "wb") as f:
        f.write(result)
    new_text = await async_azure_speech_translator.aspeech_to_text(
        audio_data=result,
        source_language="en",
    )
    assert new_text is not None
    assert new_text.lower().__contains__("hello")

async def aazure_bytes_speech_translate_hi():
    text = "नमस्कार क्या हालचाल हैं?"
    async_azure_speech_translator = AsyncAzureSpeechTranslator(
        region=region,
        token_provider=token_provider,
        resource_id=resource_id,
    )
    result = await async_azure_speech_translator.atext_to_speech(
        input_text=text,
        source_language="hi",
    )
    with open("audio.wav", "wb") as f:
        f.write(result)
    new_text = await async_azure_speech_translator.aspeech_to_text(
        audio_data=result,
        source_language="hi",
    )
    assert new_text is not None
    assert new_text.lower().__contains__("नमस्कार")
    
def test_aazure_speech_translate_en(event_loop):
    event_loop.run_until_complete(aazure_bytes_speech_translate_en())

def test_aazure_speech_translate_hi(event_loop):
    event_loop.run_until_complete(aazure_bytes_speech_translate_hi())

if __name__ == "__main__":
    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(aazure_bytes_speech_translate_hi())
    # event_loop.run_until_complete(atest_meta_batch_send_template_message())
    event_loop.close()