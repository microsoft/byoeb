import os
import asyncio
import logging
import threading
import time
import pytest
from azure.identity import get_bearer_token_provider, AzureCliCredential
from byoeb_integrations.llms.azure_openai.async_azure_openai import AsyncAzureOpenAILLM
from byoeb_integrations.llms.llama_index.llama_index_azure_openai import AsyncLLamaIndexAzureOpenAILLM
from byoeb_integrations.llms.llama_index.llama_index_openai import AsyncLLamaIndexOpenAILLM
from byoeb_integrations import test_environment_path
from dotenv import load_dotenv

load_dotenv(test_environment_path)

async def atest_llama_index_openai():
    api_key=os.getenv('OPENAI_API_KEY').strip()
    api_version = os.getenv('OPENAI_API_VERSION').strip()
    organization=os.getenv('OPENAI_ORG_ID').strip()
    model = os.getenv('OPENAI_MODEL').strip()
    llama_index_openai = AsyncLLamaIndexOpenAILLM(
        model=model,
        api_key=api_key,
        api_version=api_version,
        organization=organization,
    )
    msg = "Hello, how are you?"
    prompt = [{"role": "system", "content": "You are a helpful assistant."}]
    prompt.append({"role": "user", "content": msg})
    llm_resp, response = await llama_index_openai.agenerate_response(
        prompts=prompt
    )
    print (response)
    assert response is not None
    print(llama_index_openai.get_response_tokens(llm_resp))

if __name__ == "__main__":
    asyncio.run(atest_llama_index_openai())