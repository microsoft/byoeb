import logging
from fastapi import Request
from byoeb.factory import ChannelRegisterFactory

class ChannelRegisterHandler:
    def __init__(
        self,
        registrer_factory: ChannelRegisterFactory
    ) -> None:
        self.__registrer_factory = registrer_factory
        self.__logger = logging.getLogger(self.__class__.__name__)
        self.__logger.setLevel(logging.DEBUG)

    async def handle(
        self,
        request: Request
    ):
        return await self.__registrer_factory.get(
            channel_type="whatsapp"
        ).register(request.query_params._dict)