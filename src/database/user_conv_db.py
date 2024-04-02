import os
import datetime
import pymongo
import certifi

from database.base import BaseDB

class UserConvDB(BaseDB):
    def __init__(self, config):
        super().__init__(config)
        self.collection = self.db[config['COSMOS_USER_CONV_COLLECTION']]

    def insert_row(self,
        user_id,
        message_id,
        message_type,
        message_source_lang,
        source_language,
        message_translated,
        audio_blob_path,
        message_timestamp):

        user_conv = {
            'user_id': user_id,
            'message_id': message_id,
            'message_type': message_type,
            'message_source_lang': message_source_lang,
            'source_language': source_language,
            'message_english': message_translated,
            'audio_blob_path': audio_blob_path,
            'message_timestamp': message_timestamp
        }
        db_id = self.collection.insert_one(user_conv)
        return db_id
    
    def get_from_db_id(self, db_id):
        user_conv = self.collection.find_one({'_id': db_id})
        return user_conv

    def get_from_message_id(self, message_id):
        user_conv = self.collection.find_one({'message_id': message_id})
        return user_conv
    
    def get_all_user_conv(self, user_id):
        user_conv = self.collection.find({'user_id': user_id})
        return user_conv

    def add_llm_response(self,
        message_id,
        query_type,
        llm_response,
        citations):

        self.collection.update_one(
            {'message_id': message_id},
            {'$set': {
                'llm_response': llm_response,
                'citations': citations,
                'query_type': query_type
            }}
        )

    def add_query_type(self, message_id, query_type):
        self.collection.update_one(
            {'message_id': message_id},
            {'$set': {
                'query_type': query_type
            }}
        )

    def mark_resolved(self, message_id):
        self.collection.update_one(
            {'message_id': message_id},
            {'$set': {
                'resolved': True
            }}
        )

    def get_all_unresolved(self, from_ts, to_ts):
        user_conv = self.collection.find({"$and": [{"resolved": {"$ne": True}}, {'message_timestamp': {'$gte': from_ts, '$lt': to_ts}}]})
        return user_conv