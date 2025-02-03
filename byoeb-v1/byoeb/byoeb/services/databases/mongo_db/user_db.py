import byoeb.services.chat.constants as constants
from aiocache import Cache
from datetime import datetime, timedelta
from byoeb_core.models.byoeb.user import User
from byoeb.factory import MongoDBFactory
from typing import List, Dict, Any
from byoeb.services.databases.mongo_db.base import BaseMongoDBService

class UserMongoDBService(BaseMongoDBService):
    """Service class for user-related MongoDB operations."""

    def __init__(self, config, mongo_db_factory: MongoDBFactory):
        super().__init__(config, mongo_db_factory)
        self._history_length = self._config["app"]["history_length"]
        self.collection_name = self._config["databases"]["mongo_db"]["user_collection"]
        self.cache = Cache(Cache.MEMORY)
    
    async def invalidate_user_cache(self, user_id: str):
        print(self.cache)
        await self.cache.delete(user_id)

    async def get_user_activity_timestamp(self, user_id: str):
        """Get the user's last activity timestamp with caching."""
        cached_data = await self.cache.get(user_id)
        if cached_data is not None and isinstance(cached_data, dict):
            user = User(**cached_data)
            return user.activity_timestamp, True

        user_collection_client = await self._get_collection_client(self.collection_name)
        user_obj = await user_collection_client.afetch({"_id": user_id})

        if user_obj is None:
            return None

        user = User(**user_obj["User"])
        activity_timestamp = user.activity_timestamp

        await self.cache.set(user_id, user.model_dump(), ttl=3600)
        return activity_timestamp, False

    async def get_users(self, user_ids: List[str]) -> List[User]:
        """Fetch multiple users from the database."""
        user_collection_client = await self._get_collection_client(self.collection_name)
        users_obj = await user_collection_client.afetch_all({"_id": {"$in": user_ids}})
        return [User(**user_obj["User"]) for user_obj in users_obj]

    def user_activity_update_query(self, user: User, qa: Dict[str, Any] = None):
        """Generate update query for user activity."""
        latest_timestamp = str(int(datetime.now().timestamp()))
        update_data = {"$set": {"User.activity_timestamp": latest_timestamp}}

        if qa is None:
            return ({"_id": user.user_id}, update_data)

        last_convs = user.last_conversations
        if len(last_convs) >= self._history_length:
            last_convs.pop(0)
        last_convs.append(qa)
        update_data["$set"]["User.last_conversations"] = last_convs

        return ({"_id": user.user_id}, update_data)
    
    def aggregate_queries(
        self,
        results: List[Dict[str, Any]]
    ):
        new_user_queries = {
            constants.CREATE: [],
            constants.UPDATE: [],
        }
        for queries, _, err in results:
            if err is not None or queries is None:
                continue
            user_queries = queries.get(constants.USER_DB_QUERIES, {})
            if user_queries is not None and user_queries != {}:
                user_create_queries = user_queries.get(constants.CREATE,[])
                user_update_queries = user_queries.get(constants.UPDATE,[])
                new_user_queries[constants.CREATE].extend(user_create_queries)
                new_user_queries[constants.UPDATE].extend(user_update_queries)
        
        return new_user_queries
    
    async def execute_queries(self, queries: Dict[str, Any]):
        """Execute user database queries."""
        if not queries:
            return

        user_client = await self._get_collection_client(self.collection_name)
        if queries.get("create"):
            await user_client.ainsert(queries["create"])
        if queries.get("update"):
            await user_client.aupdate(bulk_queries=queries["update"])