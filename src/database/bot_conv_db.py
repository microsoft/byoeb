import os
import datetime
import pymongo
import certifi

from database.base import BaseDB

class BotConvDB(BaseDB):
    def __init__(self, config):
        super().__init__(config)
        self.collection = self.db['COSMOS_USER_CONV_COLLECTION']

    def insert_user_conv(self,
                        receiver_id,
                        message_id,
                        message_source,
                        message_language,
                        message_translated,
                        message_timestamp,
                        transaction_message_id):

        bot_conv = {
            'receiver_id': receiver_id,
            'message_id': message_id,
            'message_source': message_source,
            'message_language': message_language,
            'message_translated': message_translated,
            'message_timestamp': message_timestamp,
            'transaction_message_id': transaction_message_id
        }

        db_id = self.collection.insert_one(bot_conv)
        return db_id
    
    def get_from_message_id(self, message_id):
        user_conv = self.collection.find_one({'message_id': message_id})
        return user_conv
    
    def get_user_conv_by_user_id(self, user_id):
        user_conv = self.collection.find({'user_id': user_id})
        return user_conv
                        