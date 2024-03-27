import pymongo
import certifi
import os
import yaml

config_path = os.path.join(os.environ['APP_PATH'], "config.yaml")
with open(config_path, 'r') as data:
    config = yaml.safe_load(data)

import sys
sys.path.append(os.path.join(os.environ['APP_PATH'], 'src'))


from database.user_db import UserDB
from database.user_relation_db import UserRelationDB



user_db = UserDB(config)
user_relation_db = UserRelationDB(config)


user_whatsapp_id = '918375066113'
user_language = 'en'
user_type = 'Student'

expert_whatsapp_id = '918904954952'
expert_language = 'en'
expert_type = 'Teacher'

#assign user_id and expert_id, use uuid

from uuid import uuid4

user_id = str(uuid4())


user_db.insert_row(user_id, user_whatsapp_id, user_type, user_language)


expert_row = user_db.collection.find_one({'$and': [{'whatsapp_id': expert_whatsapp_id}, {'user_type': expert_type}]})
print(expert_row)
if expert_row is None:
    expert_id = str(uuid4())
    user_db.insert_row(expert_id, expert_whatsapp_id, expert_type, expert_language)
else:
    expert_id = expert_row['user_id']

user_relation_db.insert_row(user_id, expert_id, user_type, expert_type)