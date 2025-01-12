import aiohttp
import asyncio
import uuid
import json
import requests
from byoeb_core.translators.text.base import BaseTextTranslator
from azure.ai.translation.text.aio import TextTranslationClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
import logging

class AsyncAzureTextTranslator(BaseTextTranslator):
    def __init__(
        self,
        region: str,
        key = None,
        credential = None,
        resource_id: str = None,
        **kwargs
    ):
        if region is None:
            raise ValueError("region must be provided")
        if credential is None and key is None:
            raise ValueError("Either entra id credential or key must be provided")
        if credential is not None and key is not None:
            raise ValueError("Either entra id credential or key must be provided not both")
        if credential is not None and resource_id is None:
            raise ValueError("resource_id must be provided if entra id credential is provided")
        if key is not None:
            self.__credential = AzureKeyCredential(key)
        if credential is not None:
            self.__credential = credential
        self.__region = region
        self.__resource_id = resource_id
        self.__client = TextTranslationClient(
            credential=self.__credential,
            region=self.__region,
            resource_id=self.__resource_id
        )
        self.__logger = logging.getLogger(self.__class__.__name__)
    
    def translate_text(
        self,
        input_text,
        source_language,
        target_language,
        **kwargs
    ):
        raise NotImplementedError
    
    async def atranslate_text(
        self,
        input_text,
        source_language,
        target_language,
        **kwargs
    ):
        try:
            if source_language == target_language:
                return input_text
            result = await self.__client.translate(
                body=[input_text],
                to_language=[target_language],
                from_language=source_language
            )
            return result[0].translations[0].text
        except HttpResponseError as exception:
            if exception.error is not None:
                self.__logger.error(f"Error Code: {exception.error.code}")
                self.__logger.error(f"Error Message: {exception.error.message}")
            raise
    
    async def __aenter__(self):
        return await self.__client.__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.__client.__aexit__(exc_type, exc_val, exc_tb)

    async def _close(self):
        await self.__client.__aexit__()