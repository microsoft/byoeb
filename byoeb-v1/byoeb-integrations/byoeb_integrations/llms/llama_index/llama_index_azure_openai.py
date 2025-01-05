import tiktoken
from typing import Any, List, Dict
from enum import Enum
from llama_index.core.llms import ChatMessage
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.core.callbacks import CallbackManager, TokenCountingHandler
from byoeb_core.llms.base import BaseLLM

class AzureOpenAIParamsEnum(Enum):
    TEMPERATURE = "temperature"

class AsyncLLamaIndexAzureOpenAILLM(BaseLLM):
    __DEFAULT_TEMPERATURE = 0

    def __init__(
        self,
        model: str,
        deployment_name: str,
        azure_endpoint: str,
        token_provider: str = None,
        api_key: str = None,
        api_version: str = None,
        reuse_client: bool = True,
        **kwargs
    ):
        client = None
        temperature = kwargs.get(
            AzureOpenAIParamsEnum.TEMPERATURE.value,
            self.__DEFAULT_TEMPERATURE
        )
        if model is None:
            raise ValueError("model must be provided")
        token_counter = TokenCountingHandler(
            tokenizer=tiktoken.encoding_for_model(model).encode
        )
        if deployment_name is None:
            raise ValueError("deployment_name must be provided")
        if api_version is None:
            raise ValueError("api_version must be provided")
        if azure_endpoint is None:
            raise ValueError("azure_endpoint must be provided")
        if token_provider is not None:
            client = AzureOpenAI(
                use_azure_ad=True,
                model=model,
                engine=deployment_name,
                deployment_name=deployment_name,
                azure_endpoint=azure_endpoint,
                azure_ad_token_provider=token_provider,
                api_version=api_version,
                reuse_client=reuse_client,
                temperature=temperature,
                callback_manager=token_counter
            )
        elif api_key is not None:
            client = AzureOpenAI(
                use_azure_ad=True,
                model=model,
                engine=deployment_name,
                deployment_name=deployment_name,
                api_key=api_key,
                azure_endpoint=azure_endpoint,
                api_version=api_version,
                reuse_client=reuse_client,
                temperature=temperature,
                callback_manager=token_counter
            )
        else:
            raise ValueError("Either token_provider or api_key must be provided")
        self.__client = client

    def generate_response(self, query: str) -> Any:
        raise NotImplementedError
    
    def __convert_to_chat_message(
        self,
        prompts: list
    ) -> List[ChatMessage]:
        chat_messages = []
        for prompt in prompts:
            if "role" not in prompt or "content" not in prompt:
                raise ValueError("role and content must be provided in prompt")
            chat_messages.append(ChatMessage(
                role=prompt["role"],
                content=prompt["content"]
            ))
        return chat_messages
    async def agenerate_response(
        self,
        prompts: list,
        **kwargs
    ) -> Any:
        chat_messages = self.__convert_to_chat_message(prompts)
        response = await self.__client.achat(messages=chat_messages)
        return response, response.raw.choices[0].message.content.strip()
    
    def get_response_tokens(
        self,
        response: Any
    ) -> Dict[str, int]:
        total_tokens = response.raw.usage.total_tokens
        completion_tokens = response.raw.usage.completion_tokens
        prompt_tokens = response.raw.usage.prompt_tokens

        return {
            "total_tokens": total_tokens,
            "completion_tokens": completion_tokens,
            "prompt_tokens": prompt_tokens
        }
        
    def get_llm_client(self):
        return self.__client