import datetime
import sys
import yaml

import os

local_path = os.environ["APP_PATH"]
with open(local_path + "/config.yaml") as file:
    config = yaml.load(file, Loader=yaml.FullLoader)

sys.path.append(local_path.strip() + "/src")

NUM_EXPERTS = 1
from database import UserDB, UserConvDB, BotConvDB, ExpertConvDB, UserRelationDB


from messenger import WhatsappMessenger
from responder import WhatsappResponder
from conversation_database import (
    LoggingDatabase
)
import traceback

userdb = UserDB(config)
user_conv_db = UserConvDB(config)
bot_conv_db = BotConvDB(config)
expert_conv_db = ExpertConvDB(config)


import pandas as pd
from tqdm import tqdm

logger = LoggingDatabase(config)
responder = WhatsappResponder(config)

category_to_expert = {}

for expert in config["EXPERTS"]:
    category_to_expert[config["EXPERTS"][expert]] = expert
print(category_to_expert)

query_type_to_escalation_expert = {}

for expert in config["EXPERTS"]:
    print(expert)
    expert_users = list(userdb.collection.find({'$and': [{'user_type': expert}, {'escalation': True}]}))
    org_mapped_expert = {}
    for expert_user in expert_users:
        org_mapped_expert[expert_user["org_id"]] = expert_user
    query_type_to_escalation_expert[config["EXPERTS"][expert]] = org_mapped_expert
print(query_type_to_escalation_expert)

to_ts = datetime.datetime.now() - datetime.timedelta(hours=2)
from_ts = datetime.datetime.now() - datetime.timedelta(hours=4)

list_cursor = user_conv_db.get_all_unresolved(from_ts, to_ts)


df = pd.DataFrame(list_cursor)

if len(df) == 0:
    print("No unresolved queries")
    sys.exit(0)

df = df[df['query_type'] != 'small-talk']
df.reset_index(drop=True, inplace=True)
print(df)

for i, row in tqdm(df.iterrows()):
    print(row.keys())
    print(row['message_id'], row['message_english'])
    if row.get('escalated', False):
        print("Already escalated")
        continue
    try:
        user_row_lt = userdb.get_from_user_id(row["user_id"])
        # if user_row_lt['org_id'] != "TEST":
        #     continue
        query_type = row["query_type"]
        region = user_row_lt["org_id"]
        print(query_type, region)
        # print(query_type_to_escalation_expert[row["query_type"]][region], user_row_lt, row)
        responder.send_correction_poll_expert(user_row_lt, query_type_to_escalation_expert[query_type][region], row, True)
    except Exception as e:
        print(e)
        print(traceback.format_exc())

print("Escalation done")