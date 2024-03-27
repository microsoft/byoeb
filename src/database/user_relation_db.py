import os
import datetime
import pymongo
import certifi

from database.base import BaseDB

class UserRelationDB(BaseDB):
    def __init__(self, config):
        super().__init__(config)
        self.collection = self.db[config['COSMOS_RELATIONS_COLLECTION']]

    def insert_row(self,
        user_id_primary,
        user_id_secondary,
        role_primary,
        role_secondary):

        row = {
            'user_id_primary': user_id_primary,
            'user_id_secondary': user_id_secondary,
            'role_primary': role_primary,
            'role_secondary': role_secondary,
            'timestamp' : datetime.datetime.now(),
        }

        db_id = self.collection.insert_one(row)
        return db_id  
    
    def find_user_relations(self, user_id, role_secondary):
        user_relations = self.collection.find_one({'$and': [{'user_id_primary': user_id}, {'role_secondary': role_secondary}]})
        return user_relations