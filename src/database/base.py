import os
import datetime
import pymongo
import certifi

class BaseDB:
    def __init__(self, config):
        self.client = pymongo.MongoClient(os.environ["COSMOS_DB_CONNECTION_STRING"], tlsCAFile=certifi.where())
        self.db = self.client[config["COSMOS_DB_NAME"]]
