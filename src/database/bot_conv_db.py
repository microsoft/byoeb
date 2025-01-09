import os
import datetime
import pymongo
import certifi

from database.base import BaseDB

class BotConvDB(BaseDB):
    def __init__(self, config):
        super().__init__(config)
        self.collection = self.db[config['COSMOS_BOT_CONV_COLLECTION']]

    def insert_row(self,
        receiver_id,
        message_type,
        message_id,
        audio_message_id,
        message_source_lang,
        message_language,
        message_english,
        reply_id,
        citations,
        message_timestamp,
        transaction_message_id,
        message_category=None):

        bot_conv = {
            'receiver_id': receiver_id,
            'message_type': message_type,
            'message_category': message_category,
            'message_id': message_id,
            'audio_message_id': audio_message_id,
            'message_source_lang': message_source_lang,
            'message_language': message_language,
            'message_english': message_english,
            'reply_id': reply_id,
            'citations': citations,
            'message_timestamp': message_timestamp,
            'transaction_message_id': transaction_message_id
        }

        db_id = self.collection.insert_one(bot_conv)
        return db_id
                        

    def get_from_message_id(self, message_id):
        bot_conv = self.collection.find_one({'message_id': message_id})
        return bot_conv
    
    def find_with_transaction_id(self, transaction_message_id, message_type=None):
        if message_type:
            bot_conv = self.collection.find_one({'$and': [{'transaction_message_id': transaction_message_id}, {'message_type': message_type}]})
        else:
            bot_conv = self.collection.find_one({'transaction_message_id': transaction_message_id})
        return bot_conv
    
    def find_all_with_transaction_id(self, transaction_message_id, message_type=None):
        if message_type:
            bot_conv = self.collection.find({'$and': [{'transaction_message_id': transaction_message_id}, {'message_type': message_type}]})
        else:
            bot_conv = self.collection.find({'transaction_message_id': transaction_message_id})
        return bot_conv
    
    def find_with_receiver_id(self, receiver_id, message_type=None):
        if message_type:
            bot_conv = self.collection.find({'$and': [{'receiver_id': receiver_id}, {'message_type': message_type}]})
        else:
            bot_conv = self.collection.find({'receiver_id': receiver_id})
        bot_conv = list(bot_conv)
        return bot_conv
    
    def find(self, query):
        bot_conv = self.collection.find(query)
        return bot_conv