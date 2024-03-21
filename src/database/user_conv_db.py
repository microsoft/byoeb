import os
import datetime
import pymongo
import certifi

from database.base import BaseDB

class UserConvDB(BaseDB):
    def __init__(self, config):
        super().__init__(config)
        self.collection = self.db['COSMOS_USER_CONV_COLLECTION']

    def insert_user_conv(self,
                        user_id,
                        user_type,
                        message_id,
                        message_type,
                        message_source,
                        message_language,
                        message_translated,
                        audio_blob_path,
                        message_timestamp):
        user_conv = {
            'user_id': user_id,
            'user_type': user_type,
            'message_id': message_id,
            'message_type': message_type,
            'message_source': message_source,
            'message_language': message_language,
            'message_translated': message_translated,
            'audio_blob_path': audio_blob_path,
            'message_timestamp': message_timestamp
        }
        db_id = self.collection.insert_one(user_conv)
        return db_id
    
    def get_from_message_id(self, message_id):
        user_conv = self.collection.find_one({'message_id': message_id})
        return user_conv
    
    def get_user_conv_by_user_id(self, user_id):
        user_conv = self.collection.find({'user_id': user_id})
        return user_conv
                        