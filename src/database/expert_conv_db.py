import os
import datetime
import pymongo
import certifi

from database.base import BaseDB

class ExpertConvDB(BaseDB):
    def __init__(self, config):
        super().__init__(config)
        self.collection = self.db[config['COSMOS_USER_CONV_COLLECTION']]

    def insert_row(self,
        expert_whatsapp_id,
        expert_type,
        message_id):

        row = {
            'expert_whatsapp_id': expert_whatsapp_id,
            'expert_type': expert_type,
            'message_id': message_id,
            'timestamp': datetime.datetime.now()
        }

        db_id = self.collection.insert_one(row)
        return db_id
    
    def get_from_message_id(self, message_id):
        row = self.collection.find_one({'message_id': message_id})
        return row
    
