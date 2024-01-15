import pymongo
import os
import pandas as pd
import certifi
pd.options.mode.chained_assignment = None
from typing import Any
import yaml

"""
This function expires the account of the user based on a field and a given delta.
For example, if the user had the surgery more than 8 days ago, the account is expired.
"""

field = "patient_surgery_date"
num_days = 8

    
config_path = os.path.join(os.environ['APP_PATH'], 'config.yaml')
with open(config_path) as file:
    config = yaml.load(file, Loader=yaml.FullLoader)

client = pymongo.MongoClient(os.environ["COSMOS_DB_CONNECTION_STRING"], tlsCAFile=certifi.where())
db = client[config["COSMOS_DB_NAME"]]
collection = db[config["COSMOS_DB_COLLECTION"]]


cursor = collection.find()
list_cur = list(cursor)
df = pd.DataFrame(list_cur)

for row in list_cur:
    if row.get("is_expired", False):
        continue
    delta = (
        pd.Timestamp.today().date()
        - pd.to_datetime(row[field]).date()
    )
    if delta.days > num_days:
        collection.update_one({"_id": row["_id"]}, {"$set": {"is_expired": True}})