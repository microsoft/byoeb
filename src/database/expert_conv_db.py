import os
import datetime
import pymongo
import certifi

from database.base import BaseDB

class ExpertConvDB(BaseDB):
    def __init__(self, config):
        super().__init__(config)
        self.collection = self.db[config['COSMOS_EXPERT_CONV_COLLECTION']]

    def insert_row(self,
        user_id,
        message_id,
        message_type,
        message,
        reply_id,
        message_timestamp,
        transaction_message_id):

        row = {
            'user_id': user_id,
            'message_id': message_id,
            'message_type': message_type,
            'message': message,
            'reply_id': reply_id,
            'message_timestamp': message_timestamp,
            'transaction_message_id': transaction_message_id
        }

        db_id = self.collection.insert_one(row)
        return db_id
    
    def get_from_message_id(self, message_id):
        row = self.collection.find_one({'message_id': message_id})
        return row
    
    def get_from_transaction_message_id(self, transaction_message_id, message_type=None):
        if message_type:
            rows = self.collection.find({'$and': [{'transaction_message_id': transaction_message_id}, {'message_type': message_type}]})
        else:
            rows = self.collection.find({'transaction_message_id': transaction_message_id})
        rows = list(rows)
        return rows
    
    
