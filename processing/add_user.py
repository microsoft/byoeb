import pymongo
import certifi
import os
import yaml

config_path = os.path.join(os.environ['APP_PATH'], "config.yaml")
with open(config_path, 'r') as data:
    config = yaml.safe_load(data)

client = pymongo.MongoClient(os.environ["COSMOS_DB_CONNECTION_STRING"], tlsCAFile=certifi.where())
db = client[config['COSMOS_DB_NAME']]
user_collection = db[config['COSMOS_LONGTERM_COLLECTION']]
user_collection.insert_one({
    'user_id': '3',
    'Student_whatsapp_id': '919876543210',
    'Student_language': 'en',
    'Teacher_name': 'Hehe',
    'Teacher_whatsapp_id': '919876543210'
})