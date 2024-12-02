
import json
import uuid
from typing import List
import aiohttp
import logging
import asyncio
from enum import Enum
from abc import ABC, abstractmethod
from byoeb_core.models.whatsapp.requests import (
    WhatsAppMessage,
    WhatsAppInteractiveMessage,
    WhatsAppTemplateMessage,
    WhatsAppMediaMessage, 
    WhatsAppAudio,
    WhatsAppReadMessage,
    MediaData
)
from byoeb_core.models.whatsapp.response.message_response import (
    WhatsAppResponse, 
    WhatsAppResponseStatus, 
    MediaMessage
)
from byoeb_core.models.whatsapp.response.acknowledment_response import WhatsAppAcknowledgment
import requests

class StatusCode(Enum):
    SUCCESS = 200
    CREATED = 201
    ACCEPTED = 202
    ERROR = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405,
    TIMEOUT_ERROR = 408
    INTERNAL_SERVER_ERROR = 500

class WhatsAppMessageTypes(Enum):
    TEXT = "text"
    REACTION = "reaction"
    TEMPLATE = "template"
    INTERACTIVE = "interactive"
    AUDIO = "audio"
    READ = "read"

class WhatsAppRoutes(Enum):
    MESSAGE = "messages"
    MEDIA = "media"

class AsyncWhatsAppClient(ABC):
    __PRODUCT_NAME = "whatsapp"
    __BASE_URL = "https://graph.facebook.com/v21.0/"
    __DEFAULT_CONTENT_TYPE = "application/json"

    """
    Timeouts: seconds
    """
    def __init__(self,
        phone_number_id: str,
        bearer_token: str,
        reuse_client: bool = False,
        parallel_connection_count = 10,
        request_timeout = 20,
        keepalive_timeout = 60
    ):
        self.phone_number_id = phone_number_id.strip()
        self._session = None
        self._bearer_token = bearer_token.strip()
        self.root = f"{self.__BASE_URL}{self.phone_number_id}"
        self._reuse_client = reuse_client
        self._parallel_connection_count = parallel_connection_count
        self._request_timeout = request_timeout
        self._keepalive_timeout = keepalive_timeout
        self._logger = logging.getLogger(self.__class__.__name__)
    
    @classmethod
    def get_product_name(cls):
        return cls.__PRODUCT_NAME
    
    def __prepare_data(
        self,
        data,
        files,
    ):
        form_data = aiohttp.FormData()
        if data:
            for key, value in data.items():
                form_data.add_field(key, value)

        if files:
            # Add file fields
            for file_key, file_info in files.items():
                file_path, file_obj, file_content_type = file_info
                form_data.add_field(
                    file_key,
                    file_obj,
                    filename=file_path,
                    content_type=file_content_type
                )
        return form_data
    
    def __get_headers__(
        self,
        content_type: str = None
    ):
        """
        Constructs the headers for the request.

        Args:
            content_type (str): The content type header for the request, if applicable.

        Returns:
            dict: A dictionary of headers.
        """
        headers = {
            "Authorization": f"Bearer {self._bearer_token.strip()}"
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    async def __get_session(self):
        if self._session is None:
            # Customize connection settings here
            timeout = aiohttp.ClientTimeout(total=self._request_timeout)
            connector = aiohttp.TCPConnector(
                limit_per_host=self._parallel_connection_count,
                keepalive_timeout=self._keepalive_timeout
            )
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector
            )
        if self._reuse_client:
            return self._session
        else:
            await self._session.close()
            self._session = aiohttp.ClientSession()
            return self._session
    
    def get_send_function(self, type):
        if type == WhatsAppMessageTypes.TEXT.value:
            return self.asend_text_message
        elif type == WhatsAppMessageTypes.REACTION.value:
            return self.asend_reaction
        elif type == WhatsAppMessageTypes.INTERACTIVE.value:
            return self.asend_interactive_message
        elif type == WhatsAppMessageTypes.TEMPLATE.value:
            return self.asend_template_message
        elif type == WhatsAppMessageTypes.AUDIO.value:
            return self.asend_audio_message
        elif type == WhatsAppMessageTypes.READ.value:
            return self.amark_as_read
        
    
    
    async def __upload__(
        self,
        url,
        data: aiohttp.FormData,
    ):
        session = await self.__get_session()
        headers = {
            "Authorization": f"Bearer {self._bearer_token.strip()}",
        }
        try:
            async with session.post(
                url,
                headers=headers,
                data=data
            ) as response:
                json_response = await response.json()
                status = response.status
                if status == StatusCode.SUCCESS.value:
                    return status, json_response, None
                
                if status == StatusCode.ACCEPTED.value:
                    return status, json_response, None
                
                else:
                    return status, None, json_response.get("error")
            
        except asyncio.TimeoutError as e:
            self._logger.error(f"Timeout error: {e}")
            return StatusCode.TIMEOUT_ERROR.value, None, e
        
        except Exception as e:
            self._logger.error(f"Error: {e}")
            return StatusCode.INTERNAL_SERVER_ERROR.value, None, e
    
    async def __delete__(
        self,
        url
    ):
        session = await self.__get_session()
        headers = self.__get_headers__()
        try:
            async with session.delete(
                url,
                headers=headers
            ) as response:
                status = response.status
                json_response = await response.json()
                if status == StatusCode.SUCCESS.value:
                    return status, json_response, None
                
                if status == StatusCode.ACCEPTED.value:
                    return status, json_response, None
                
                else:
                    return status, None, json_response
        except asyncio.TimeoutError as e:
            self._logger.error(f"Timeout error: {e}")
            return StatusCode.TIMEOUT_ERROR.value, None, e

        except Exception as e:
            self._logger.error(f"Error: {e}")
            return StatusCode.INTERNAL_SERVER_ERROR.value, None, e
        
    async def __get__(
        self,
        url
    ):
        session = await self.__get_session()
        headers = self.__get_headers__()
        try:
            async with session.get(
                url,
                headers=headers
            ) as response: 
                status = response.status
                content = await response.content.read()
                if status == StatusCode.SUCCESS.value:
                    return status, content, None
                
                if status == StatusCode.ACCEPTED.value:
                    return status, content, None
                
                else:
                    return status, None, content
        except asyncio.TimeoutError as e:
            self._logger.error(f"Timeout error: {e}")
            return StatusCode.TIMEOUT_ERROR.value, None, e

        except Exception as e:
            self._logger.error(f"Error: {e}")
            return StatusCode.INTERNAL_SERVER_ERROR.value, None, e
        
    async def __post__(
        self,
        url: str,
        payload=None,
        data: aiohttp.FormData = None,
        content_type: str = "application/json"
    ):
        """
        Sends a POST request to the given URL.

        Args:
            url (str): The endpoint URL.
            payload: The JSON payload for the request.
            data (aiohttp.FormData, optional): The form data for file uploads.
            content_type (str): The content type header for the request.

        Returns:
            tuple: (status code, response JSON, error)
        """
        # Set headers based on whether data or payload is provided
        headers = self.__get_headers__(content_type if data is None else None)
        session = await self.__get_session()
        if payload is not None and data is not None:
            raise ValueError("Only one of payload or data should be provided.")
        try:
            async with session.post(
                url,
                headers=headers,
                json=payload,
                data=data
            ) as response:
                json_response = await response.json()
                status = response.status
                if status == StatusCode.SUCCESS.value:
                    return status, json_response, None
                
                if status == StatusCode.ACCEPTED.value:
                    return status, json_response, None
                
                else:
                    return status, None, json_response

        except asyncio.TimeoutError as e:
            self._logger.error(f"Timeout error: {e}")
            return StatusCode.TIMEOUT_ERROR.value, None, e

        except Exception as e:
            self._logger.error(f"Error: {e}")
            return StatusCode.INTERNAL_SERVER_ERROR.value, None, e
    
    async def _upload_media(
        self,
        media_data: bytes,
        mime_type: str
    ):
        url = f"{self.root}/{WhatsAppRoutes.MEDIA.value}"
        data = {
            "messaging_product": self.__PRODUCT_NAME
        }
        file_name = str(uuid.uuid4())
        files = {
            "file": [file_name, media_data, mime_type]
        }
        upload_data = self.__prepare_data(data, files)
        return await self.__post__(url, data=upload_data)
    
    async def adownload_media(
        self,
        media_id: str
    ):
        url = f"{self.__BASE_URL}/{media_id}"
        status, response, err = await self.__get__(url)
        json_response = json.loads(response)
        data_url = json_response.get("url")
        mime_type = json_response.get("mime_type")
        status, response, err = await self.__get__(data_url)
        return status, MediaData(
            data=response,
            mime_type=mime_type
        ), err
    
    async def asend_text_message(
        self,
        payload: dict
    ) -> WhatsAppResponse:
        whatsapp_text_message = WhatsAppMessage.model_validate(payload)
        route = WhatsAppRoutes.MESSAGE.value
        url = f"{self.root}/{route}"
        status, response, err = await self.__post__(url, payload)
        if (status != StatusCode.ACCEPTED.value
            and status != StatusCode.SUCCESS.value
        ):
            return WhatsAppResponse(
                response_status=WhatsAppResponseStatus(
                    status=str(status),
                    error=str(err)
                ),
                messaging_product=whatsapp_text_message.messaging_product,
                contacts=[],
                messages=[]
            )
        whatsapp_response = WhatsAppResponse.model_validate(response)
        whatsapp_response.response_status=WhatsAppResponseStatus(
            status=str(status),
            error=str(err)
        )
        return whatsapp_response
    
    async def asend_reaction(
        self,
        payload: dict
    ) -> WhatsAppResponse:
        whatsapp_text_message = WhatsAppMessage.model_validate(payload)
        route = WhatsAppRoutes.MESSAGE.value
        url = f"{self.root}/{route}"
        json_dict = whatsapp_text_message.model_dump()
        status, response, err = await self.__post__(url, json_dict)
        if (status != StatusCode.ACCEPTED.value
            and status != StatusCode.SUCCESS.value
        ):
            return WhatsAppResponse(
                response_status=WhatsAppResponseStatus(
                    status=str(status),
                    error=str(err)
                ),
                messaging_product=whatsapp_text_message.messaging_product,
                contacts=[],
                messages=[]
            )
        whatsapp_response = WhatsAppResponse.model_validate(response)
        whatsapp_response.response_status=WhatsAppResponseStatus(
            status=str(status),
            error=str(err)
        )
        return whatsapp_response
    
    async def asend_interactive_message(
        self,
        payload: dict
    ) -> WhatsAppResponse:
        whatsapp_interactive_message = WhatsAppInteractiveMessage.model_validate(payload)
        route = WhatsAppRoutes.MESSAGE.value
        url = f"{self.root}/{route}"
        status, response, err = await self.__post__(url, payload)
        if (status != StatusCode.ACCEPTED.value
            and status != StatusCode.SUCCESS.value
        ):
            return WhatsAppResponse(
                response_status=WhatsAppResponseStatus(
                    status=str(status),
                    error=str(err)
                ),
                messaging_product=whatsapp_interactive_message.messaging_product,
                contacts=[],
                messages=[]
            )
        whatsapp_response = WhatsAppResponse.model_validate(response)
        whatsapp_response.response_status=WhatsAppResponseStatus(
            status=str(status),
            error=str(err)
        )
        return whatsapp_response

    async def asend_template_message(
        self,
        payload: dict
    ) -> WhatsAppResponse:
        whatsapp_template_message = WhatsAppTemplateMessage.model_validate(payload)
        route = WhatsAppRoutes.MESSAGE.value
        url = f"{self.root}/{route}"
        status, response, err = await self.__post__(url, payload)
        if (status != StatusCode.ACCEPTED.value
            and status != StatusCode.SUCCESS.value
        ):
            return WhatsAppResponse(
                response_status=WhatsAppResponseStatus(
                    status=str(status),
                    error=str(err)
                ),
                messaging_product=whatsapp_template_message.messaging_product,
                contacts=[],
                messages=[]
            )
        whatsapp_response = WhatsAppResponse.model_validate(response)
        whatsapp_response.response_status=WhatsAppResponseStatus(
            status=str(status),
            error=str(err)
        )
        return whatsapp_response

    async def asend_audio_message(
        self,
        payload: dict
    ) -> WhatsAppResponse:
        
        # Upload media
        whatsapp_audio_context = WhatsAppMediaMessage.model_validate(payload)
        audio = whatsapp_audio_context.audio
        if audio is None:
            status, response, err = await self._upload_media(
                whatsapp_audio_context.media.data,
                whatsapp_audio_context.media.mime_type
            )
            if err:
                return WhatsAppResponse(
                    response_status=WhatsAppResponseStatus(
                        status=str(status),
                        error=str(err)
                    ),
                    messaging_product=whatsapp_audio_context.messaging_product,
                    contacts=[],
                    messages=[]
                )
            audio = WhatsAppAudio.model_validate(response)

        # Send media message
        whatsapp_audio_message = WhatsAppMediaMessage(
            messaging_product=whatsapp_audio_context.messaging_product,
            type=whatsapp_audio_context.type,
            to=whatsapp_audio_context.to,
            audio=audio,
            context=whatsapp_audio_context.context,
        )
        payload = whatsapp_audio_message.model_dump()
        message_url = f"{self.root}/{WhatsAppRoutes.MESSAGE.value}"
        status, response, err = await self.__post__(message_url, payload)
        if (status != StatusCode.ACCEPTED.value
            and status != StatusCode.SUCCESS.value
        ):
            return WhatsAppResponse(
                response_status=WhatsAppResponseStatus(
                    status=str(status),
                    error=str(err)
                ),
                messaging_product=whatsapp_audio_message.messaging_product,
                contacts=[],
                messages=[]
            ), audio
        whatsapp_response = WhatsAppResponse.model_validate(response)
        whatsapp_response.media_message=MediaMessage(
            id = audio.id
        )
        whatsapp_response.response_status=WhatsAppResponseStatus(
            status=str(status),
            error=str(err)
        )
        return whatsapp_response
    
    async def amark_as_read(
        self,
        message_id: str
    ) -> WhatsAppAcknowledgment:
        route = WhatsAppRoutes.MESSAGE.value
        url = f"{self.root}/{route}"
        payload = WhatsAppReadMessage(
            messaging_product=self.__PRODUCT_NAME,
            status="read",
            message_id=message_id
        ).model_dump()
        status, response, err = await self.__post__(url, payload)
        response_status = WhatsAppResponseStatus(
            status=str(status),
            error=str(err)
        )
        if response is not None:
            whatsapp_read_ack = WhatsAppAcknowledgment.model_validate(response)
            whatsapp_read_ack.response_status=response_status
            return whatsapp_read_ack
        elif err is not None:
            whatsapp_read_ack = WhatsAppAcknowledgment.model_validate(err)
            whatsapp_read_ack.response_status=response_status
            return whatsapp_read_ack
        return WhatsAppAcknowledgment(
            response_status=response_status
        )
    
    async def adelete_media(
        self,
        media_id: str
    ) -> WhatsAppAcknowledgment:
        url = f"{self.__BASE_URL}/{media_id}"
        status, response, err = await self.__delete__(url)
        whatsapp_delete_ack = WhatsAppAcknowledgment().model_validate(response)
        whatsapp_delete_ack.response_status=WhatsAppResponseStatus(
            status=str(status),
            error=str(err)
        )
        return whatsapp_delete_ack

    async def asend_batch_messages(
        self,
        payloads: list,
        message_type: str
    ) -> List[WhatsAppResponse]:
        tasks = []
        send_function = self.get_send_function(message_type)
        for payload in payloads:
            tasks.append(send_function(payload))
        responses = await asyncio.gather(*tasks)
        batch_responses = []
        for response in responses:
            whatsapp_text_response: WhatsAppResponse = response
            batch_responses.append(whatsapp_text_response)
        return batch_responses
    
    async def __aenter__(self):
        await self.__get_session()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._session:
            await self._session.close()

    async def _close(self):
        if self._session:
            await self._session.close()
            self._session = None
        