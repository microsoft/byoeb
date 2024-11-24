import json
import byoeb.services.user.utils as user_utils
from typing import List, Any
from byoeb.services.user.user import UserService
from byoeb_core.models.byoeb.response import ByoebResponseModel, ByoebStatusCodes
from byoeb_core.models.byoeb.user import User 
from byoeb.app.configuration.config import app_config, bot_config
from byoeb.factory import MongoDBFactory
from byoeb_core.databases.mongo_db.base import BaseDocumentCollection
from byoeb_integrations.databases.mongo_db.azure.async_azure_cosmos_mongo_db import AsyncAzureCosmosMongoDB, AsyncAzureCosmosMongoDBCollection

class UsersHandler:
    _user_service = None
    def __init__(
        self,
        db_provider: str,
        mongo_db_facory: MongoDBFactory
    ) -> None:
        self.__mongo_db_facory = mongo_db_facory
        self.__db_provider = db_provider
        self.__user_collection = app_config["databases"]["mongo_db"]["user_collection"]
        self.__mongo_db = None
        self.__user_collection_client = None
        self.__regular_user_type = bot_config["regular"]["user_type"]
        self.__expert_user_type = bot_config["expert"]["user_type"]

    async def get_collection_client(self) -> BaseDocumentCollection:
        if self.__user_collection_client is not None:
            return self.__user_collection_client
        self.__mongo_db = await self.__mongo_db_facory.get(self.__db_provider)
        if isinstance(self.__mongo_db, AsyncAzureCosmosMongoDB):
            self.__user_collection_client = AsyncAzureCosmosMongoDBCollection(
                collection=self.__mongo_db.get_collection(self.__user_collection)
            )
        return self.__user_collection_client
    
    async def get_or_create_user_service(self) -> UserService:
        if self._user_service is not None:
            return self._user_service
        self._user_service = UserService(
            collection_client=await self.get_collection_client(),
            bot_config=bot_config
        )
        return self._user_service
    
    async def aregister(
        self,
        data: list
    ) -> ByoebResponseModel:
        user_svc = await self.get_or_create_user_service()
        byoeb_users = []
        byoeb_messages = []
        for user in data:
            byoeb_user = User(**user)
            if byoeb_user.phone_number_id is None:
                message = "Phone number id must be provided"
                byoeb_messages.append(user_utils.get_register_message(byoeb_user, message))
                continue
            if byoeb_user.user_language is None:
                message = "User language must be provided"
                byoeb_messages.append(user_utils.get_register_message(byoeb_user, message))
                continue
            if byoeb_user.user_type is None:
                message = "User type must be provided"
                byoeb_messages.append(user_utils.get_register_message(byoeb_user, message))
                continue
            if byoeb_user.user_type != self.__regular_user_type and byoeb_user.user_type != self.__expert_user_type:
                message = f"""Invalid user type. Available user types 
                are {self.__regular_user_type} and {self.__expert_user_type}"""
                byoeb_messages.append(user_utils.get_register_message(byoeb_user, message))
                continue
            if (byoeb_user.user_type == self.__regular_user_type and len(byoeb_user.audience) != 0):
                message = "Cannot have list of audience"
                byoeb_messages.append(user_utils.get_register_message(byoeb_user, message))
                continue
            if (
                byoeb_user.user_type == self.__regular_user_type
                and byoeb_user.experts is not None
                and byoeb_user.phone_number_id in byoeb_user.experts
            ):
                message = "Cannot be in their own list of experts"
                byoeb_messages.append(user_utils.get_register_message(byoeb_user, message))
                continue
            if (byoeb_user.user_type == self.__expert_user_type and len(byoeb_user.experts) != 0):
                message =  "Cannot have list of experts"
                byoeb_messages.append(user_utils.get_register_message(byoeb_user, message))
                continue
            if (
                byoeb_user.user_type == self.__expert_user_type
                and byoeb_user.audience is not None
                and byoeb_user.phone_number_id in byoeb_user.audience
            ):
                message = "Cannot be in their own list of audience"
                byoeb_messages.append(user_utils.get_register_message(byoeb_user, message))
                continue
            byoeb_users.append(byoeb_user)

        if len(byoeb_messages) > 0:
            return ByoebResponseModel(
                status_code=ByoebStatusCodes.BAD_REQUEST.value,
                message=byoeb_messages
            )
        results = await user_svc.aregister(byoeb_users)
        return ByoebResponseModel(
            status_code=ByoebStatusCodes.OK.value,
            message=results
        )
    
    async def adelete(
        self,
        phone_number_ids: Any
    ):
        if not isinstance(phone_number_ids, list):
            return ByoebResponseModel(
                status_code=ByoebStatusCodes.BAD_REQUEST.value,
                message="Provide list of phone number ids"
            )
        user_svc = await self.get_or_create_user_service()
        results = await user_svc.adelete(
            phone_number_ids=phone_number_ids
        )
        return ByoebResponseModel(
            status_code=ByoebStatusCodes.OK.value,
            message=results
        )
    
    async def aupdate(
        self,
        data: str
    ):
        user_collection_client = await self.get_collection_client()
        
    async def aget(
        self,
        phone_number_ids: Any
    ):
        if not isinstance(phone_number_ids, list):
            return ByoebResponseModel(
                status_code=ByoebStatusCodes.BAD_REQUEST.value,
                message="Provide list of phone number ids"
            )
        user_svc = await self.get_or_create_user_service()
        results = await user_svc.aget(
            phone_number_ids=phone_number_ids
        )
        return ByoebResponseModel(
            status_code=ByoebStatusCodes.OK.value,
            message=results
        )