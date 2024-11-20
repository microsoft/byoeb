import logging
import os
from byoeb_core.channel.base import BaseChannelRegister
from byoeb_core.models.byoeb.response import ByoebResponseModel

class RegisterWhatsapp(BaseChannelRegister):
    """
    A class to handle the registration process for 
    Whatsapp by implementing the RegisterAppInterface.

    Methods
    -------
    register(request: str) -> ResponseModel
        Handles the registration request and returns a ResponseModel object.
        
    __get_response(request) -> ResponseModel
        A private method that simulates getting a response for 
        the registration request and returns a ResponseModel object.
    """

    __REQUESST_MODE = "hub.mode"
    __REQUEST_TOKEN = "hub.verify_token"
    __REQUEST_CHALLENGE = "hub.challenge"

    __MODE_TYPE = "subscribe"

    def __init__(
        self,
        verification_token: str
    ) -> None:
        self.__logger = logging.getLogger(self.__class__.__name__)
        self.__verification_token = verification_token.strip()

    async def register(
        self,
        params: dict,
        **kwargs
    ) -> ByoebResponseModel:
        self.__logger.debug(msg="Registering Whatsapp")
        self.__logger.debug(self.__hash__)
        response = self.__get_response(params, self.__verification_token)
        return response

    def __is_invalid(
        self,
        value: str
    ):
        return value in (None, '', 'null')
    def __get_response(
        self,
        params: dict,
        verification_token: str
    ) -> ByoebResponseModel:
        mode = params.get(self.__REQUESST_MODE)
        token = params.get(self.__REQUEST_TOKEN)
        challenge = params.get(self.__REQUEST_CHALLENGE)

        if (self.__is_invalid(mode) or
            self.__is_invalid(token) or
            self.__is_invalid(challenge)
        ):
            return ByoebResponseModel(
                message="Invalid request to register whatsapp",
                status_code=400
            )

        if mode != self.__MODE_TYPE:
            return ByoebResponseModel(
                message="Invalid mode type",
                status_code=400
            )

        if token != self.__verification_token:
            return ByoebResponseModel(
                message="Invalid verification token",
                status_code=400
            )

        return ByoebResponseModel(
            message=challenge,
            status_code=200
        )
