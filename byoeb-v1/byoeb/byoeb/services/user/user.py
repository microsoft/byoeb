
import byoeb.services.user.utils as user_utils
import hashlib
from datetime import datetime
from typing import List, Dict, Any
from byoeb_core.models.byoeb.user import User
from byoeb.services.user.base import BaseUserService
from byoeb_core.databases.mongo_db.base import BaseDocumentCollection

class UserService(BaseUserService):
    def __init__(
        self,
        collection_client: BaseDocumentCollection,
        bot_config
    ):
        self.__collection_client = collection_client
        self.__regular_user_type = bot_config["regular"]["user_type"]
        self.__expert_user_types = bot_config["expert"].values()

    def __prepare_user_insert_data(
        self,
        byoeb_users: List[User]
    ):
        json_data_users = []
        for user in byoeb_users:
            json_data_users.append({
                "_id": user.user_id,
                "User": user.model_dump(),
                "timestamp": str(int(datetime.now().timestamp()))
            })
        return json_data_users
    
    def __validate_expert_user_type(
        self,
        expert_user_type: str
    ) -> bool:
        if expert_user_type in self.__expert_user_types:
            return True
        return False
    
    async def __get_post_insert_user_delete_query(
        self,
        ids: List[str],
        user: User
    ):
        relation_numbers = user.audience + user_utils.get_experts_numbers(user.experts)
        user_ids = user_utils.get_user_ids_from_phone_number_ids(relation_numbers)
        _, present_ids = user_utils.get_missing_and_present_ids(ids, user_ids)

        # get wrong relations
        wrong_relation_numbers = []
        present_relations = await self.__get_users_data(present_ids)
        for present_relation in present_relations:
            if user.user_type == present_relation.user_type:
                wrong_relation_numbers.append(present_relation.phone_number_id)
        if len(wrong_relation_numbers) != 0:
            delete_query = {"_id": user.user_id}
            return delete_query, wrong_relation_numbers
        return None, wrong_relation_numbers
    
    async def __get_post_insert_user_update_query(
        self,
        ids: List[str],
        user: User
    ):
        relation_numbers = user.audience + user_utils.get_experts_numbers(user.experts)
        user_ids = user_utils.get_user_ids_from_phone_number_ids(relation_numbers)
        missing_ids, _ = user_utils.get_missing_and_present_ids(ids, user_ids)
        
        # gets missing numers
        missing_numbers = []
        for number in relation_numbers:
            hex_id = hashlib.md5(number.encode()).hexdigest()
            if hex_id in missing_ids:
                missing_numbers.append(number)
        update_user = User(**user.model_dump())
        if update_user.user_type == self.__regular_user_type:
            update_experts = {
                key: [item for item in value if item not in missing_numbers] if value else value
                for key, value in update_user.experts.items()
            }
            update_user.experts = update_experts
        elif self.__validate_expert_user_type(update_user.user_type):
            update_user.audience = list(set(update_user.audience) - set(missing_numbers))

        if len(missing_numbers) != 0:
            update_query = (
                {"_id": update_user.user_id},
                {"$set": {"User": update_user.model_dump()}}
            )

            return update_query, missing_numbers
        return None, missing_numbers

    def __add_user_to_expert_relations(
            self,
            experts: Dict[str, List[str]],
            user_relations: List[Dict[str, Any]],
        ) -> Dict[str, List[str]]:
        # Create a copy of experts to avoid modifying the original input
        updated_experts = experts.copy()

        for relation in user_relations:
            user_type = relation["user_type"]
            phone_number_id = relation["phone_number_id"]
            
            # Initialize the list if the user_type doesn't exist in updated_experts
            if user_type not in updated_experts:
                updated_experts[user_type] = []
            
            # Append the phone_number_id to the appropriate user_type list
            updated_experts[user_type].append(phone_number_id)
        
        # Remove duplicates by converting to set and back to list, but avoid modifying the original
        for key, value in updated_experts.items():
            updated_experts[key] = list(set(value))
        
        return updated_experts

    
    def __add_expert_to_user_relations(
        self,
        audience: List[str],
        user_relations: List[Dict[str, Any]],
    ):
        new_audience = []
        for relation in user_relations:
            new_audience.append(relation["phone_number_id"])
        return list(set(audience + new_audience))
    
    def __remove_user_to_expert_relations(
        self,
        experts: Dict[str, List[str]],
        user_relations: List[Dict[str, Any]],
    ):
        remove_numbers = []
        for relation in user_relations:
            remove_numbers.append(relation["phone_number_id"])
        updated_experts = {
            key: [item for item in value if item not in remove_numbers] if value else value
            for key, value in experts.items()
        }
        return updated_experts
    
    def __remove_expert_to_user_relations(
        self,
        audience: List[str],
        user_relations: List[Dict[str, Any]],
    ):
        new_audience = []
        for relation in user_relations:
            new_audience.append(relation["phone_number_id"])
        return list(set(audience) - set(new_audience))
    
    def __get_add_relation_update_queries_for_affected_users(
        self,
        users_data: List[User],
        relations: Dict[str, List[str]],
    ) -> list:
        update_queries = []
        for user in users_data:
            user_relations = relations[user.user_id]
            if user.user_type == self.__regular_user_type:
                user.experts = self.__add_user_to_expert_relations(user.experts, user_relations)
            elif self.__validate_expert_user_type(user.user_type):
                user.audience = self.__add_expert_to_user_relations(user.audience, user_relations)
            update_query = (
                {"_id": user.user_id},
                {"$set": {"User": user.model_dump()}}
            )
            update_queries.append(update_query)
        return update_queries

    def __get_remove_relation_update_queries_for_affected_users(
        self,
        users_data: List[User],
        relations: Dict[str, List[str]],
    ) -> list:
        update_queries = []
        for user in users_data:
            user_relations = relations[user.user_id]
            if user.user_type == self.__regular_user_type:
                user.experts = self.__remove_user_to_expert_relations(user.experts, user_relations)
            elif self.__validate_expert_user_type(user.user_type):
                user.audience = self.__remove_expert_to_user_relations(user.audience, user_relations)
            update_query = ({"_id": user.user_id}, {"$set": {"User": user.model_dump()}})
            update_queries.append(update_query)
        return update_queries
        
    async def __get_post_insert_users_queries(
        self,
        ids,
        byoeb_users: List[User]
    ) -> list:
        byoeb_messages = []
        update_queries = []
        delete_queries = []
        for user in byoeb_users:
            delete_query, wrong_relation_numbers = await self.__get_post_insert_user_delete_query(ids, user)
            update_query, missing_numbers = await self.__get_post_insert_user_update_query(ids, user)
            if delete_query is not None:
                message = f"Not registered. Conflict in user relation {wrong_relation_numbers}. One or more users are of same type"
                byoeb_messages.append(user_utils.get_register_message(user, message))
                delete_queries.append(delete_query)
            elif update_query is not None:
                message = f"Successfully Registered. Skipped adding, users not found, in user relation {missing_numbers}"
                byoeb_messages.append(user_utils.get_register_message(user, message))
                update_queries.append(update_query)
            else:
                message = "Successfully Registered"
                byoeb_messages.append(user_utils.get_register_message(user, message))
        return byoeb_messages, update_queries, delete_queries
    
    async def __get_users_data(
        self,
        user_ids: List[str],
    ) -> List[User]:
        query = {"_id": {"$in": user_ids}}
        documents = await self.__collection_client.afetch_all(query)
        users_data: List[User] = []
        for document in documents:
            user_data = document['User']
            users_data.append(User(**user_data))
        return users_data
    
    async def aregister(
        self,
        users: List[User]
    ) -> str:
        byoeb_users: List[User] = []
        byoeb_messages = []
        ids = await self.__collection_client.afetch_ids()
        for user in users:
            user_id = hashlib.md5(user.phone_number_id.encode()).hexdigest()
            if user_id in ids:
                message = "Already registered. Please use update or delete and add again"
                byoeb_messages.append(user_utils.get_register_message(user, message))
                continue
            new_user = User(
                user_id=hashlib.md5(user.phone_number_id.encode()).hexdigest(),
                phone_number_id=user.phone_number_id,
                user_language=user.user_language,
                user_type=user.user_type,
                experts=user.experts,
                audience=user.audience,
                created_timestamp = str(int(datetime.now().timestamp())),
                activity_timestamp = str(int(datetime.now().timestamp()))
            )
            byoeb_users.append(new_user)
        json_data_users = self.__prepare_user_insert_data(byoeb_users)
        inserted_ids, _ = await self.__collection_client.ainsert(json_data_users)
        print(inserted_ids)
        ids = list(set(ids + inserted_ids))
        messages, update_queries, delete_queries = await self.__get_post_insert_users_queries(ids, byoeb_users)
        await self.__collection_client.aupdate(bulk_queries=update_queries)
        await self.__collection_client.adelete(bulk_queries=delete_queries)
        affected_keys, add_relations = user_utils.get_relations_update(ids, byoeb_users)
        affected_users = await self.__get_users_data(affected_keys)
        update_queries = self.__get_add_relation_update_queries_for_affected_users(affected_users, add_relations)
        await self.__collection_client.aupdate(bulk_queries=update_queries)
        byoeb_messages.extend(messages)
        return byoeb_messages
    
    async def adelete(
        self,
        phone_number_ids: List[str]
    ) -> str:
        ids = await self.__collection_client.afetch_ids()
        delete_ids = user_utils.get_user_ids_from_phone_number_ids(phone_number_ids)
        missing_ids, valid_delete_ids = user_utils.get_missing_and_present_ids(ids, delete_ids)
        users_data = await self.__get_users_data(valid_delete_ids)
        delete_queries = [{"_id": id} for id in valid_delete_ids]
        await self.__collection_client.adelete(bulk_queries=delete_queries)
        left_ids = list(set(ids) - set(valid_delete_ids))
        affected_keys, delete_relations = user_utils.get_relations_update(left_ids, users_data)
        affected_users_data = await self.__get_users_data(affected_keys)
        update_queries = self.__get_remove_relation_update_queries_for_affected_users(affected_users_data, delete_relations)
        await self.__collection_client.aupdate(bulk_queries=update_queries)
        return user_utils.get_delete_messages(phone_number_ids, missing_ids)

    async def aget(
        self,
        phone_number_ids: List[str]
    ) -> List[str]:
        user_ids = user_utils.get_user_ids_from_phone_number_ids(phone_number_ids)
        users_data = await self.__get_users_data(user_ids)
        fetched_ids = [user.phone_number_id for user in users_data]
        missing_ids, _ = user_utils.get_missing_and_present_ids(phone_number_ids, fetched_ids)
        byoeb_messages = []
        for user in users_data:
            byoeb_messages.append(user.model_dump())
        for missing_id in missing_ids:
            byoeb_messages.append({
                "phone_number_id": missing_id,
                "message": "User not found"
            })
        return byoeb_messages
    
    async def aupdate(
        self,
        data: User
    ) -> str:
        pass