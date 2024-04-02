import os
import datetime
import pymongo
import certifi

from database.base import BaseDB

class UserDB(BaseDB):
    def __init__(self, config):
        super().__init__(config)
        self.collection = self.db[config['COSMOS_USER_COLLECTION']]

    def insert_row(self,
        user_id,
        whatsapp_id,
        user_type,
        user_language):

        user = {
            'user_id': user_id,
            'whatsapp_id': whatsapp_id,
            'user_type': user_type,
            'user_language': user_language,
            'timestamp' : datetime.datetime.now(),
        }
        db_id = self.collection.insert_one(user)
        return db_id
    
    def get_from_user_id(self, user_id):
        user = self.collection.find_one({'user_id': user_id})
        return user
    
    def get_from_whatsapp_id(self, whatsapp_id):
        user = self.collection.find_one({'whatsapp_id': whatsapp_id})
        return user
    
    def update_user_language(self, user_id, user_language):
        self.collection.update_one(
            {'user_id': user_id},
            {'$set': {
                'user_language': user_language
            }}
        )
    
    def get_random_expert(self, expert_type, number_of_experts):
        pipeline = [
            {"$match": {"user_type": expert_type}},
            {"$sample": {"size": number_of_experts}}
        ]
        experts = list(self.collection.aggregate(pipeline))
        return experts