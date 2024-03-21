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
        message_timestamp,
        transaction_message_id):

        bot_conv = {
            'receiver_id': receiver_id,
            'message_type': message_type,
            'message_id': message_id,
            'audio_message_id': audio_message_id,
            'message_source_lang': message_source_lang,
            'message_language': message_language,
            'message_english': message_english,
            'message_timestamp': message_timestamp,
            'transaction_message_id': transaction_message_id
        }

        db_id = self.collection.insert_one(bot_conv)
        return db_id
                        

    def get_from_message_id(self, message_id):
        bot_conv = self.collection.find_one({'message_id': message_id})
        return bot_conv