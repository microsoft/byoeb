import os
import datetime
import pymongo
import certifi
from uuid import uuid4
from database.base import BaseDB

class UserDB(BaseDB):
    def __init__(self, config):
        super().__init__(config)
        self.collection = self.db[config['COSMOS_USER_COLLECTION']]

    def insert_row(self,
        user_id,
        whatsapp_id,
        user_type,
        user_language,
        org_id = 'BLR',
        meta: dict = None):

        user = {
            'user_id': user_id,
            'whatsapp_id': whatsapp_id,
            'user_type': user_type,
            'user_language': user_language,
            'org_id': org_id,
            'timestamp' : datetime.datetime.now(),
        }
        if meta:
            user.update(meta)
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

    def add_or_update_related_qns(self, user_id, related_qns):
        self.collection.update_one(
            {'user_id': user_id},
            {'$set': {
            'related_qns': related_qns
            }},
            upsert=True
        )

    def get_related_qns(self, user_id):
        user = self.collection.find_one({'user_id': user_id})
        return user.get('related_qns', [])

    