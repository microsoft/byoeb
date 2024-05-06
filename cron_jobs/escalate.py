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
query_type_to_escalation_expert = {
}

for expert in config["EXPERTS"]:
    query_type_to_escalation_expert[config["EXPERTS"][expert]] = userdb.collection.find_one({"$and": [{"user_type": expert}, {"escalation": True}]})
print(query_type_to_escalation_expert)

to_ts = datetime.datetime.now() - datetime.timedelta(hours=0)
from_ts = datetime.datetime.now() - datetime.timedelta(days=1)

list_cursor = user_conv_db.get_all_unresolved(from_ts, to_ts)

df = pd.DataFrame(list_cursor)
df = df[df['query_type'] != 'small-talk']
df.reset_index(drop=True, inplace=True)

for i, row in tqdm(df.iterrows()):
    print(row.keys())
    # print(row['message_id'], row['message_english'])
    try:
        user_row_lt = userdb.get_from_user_id(row["user_id"])
        print(query_type_to_escalation_expert[df.loc[i, "query_type"]], user_row_lt, row)
        responder.send_correction_poll_expert(user_row_lt, query_type_to_escalation_expert[df.loc[i, "query_type"]], row, True)
    except Exception as e:
        print(e)

    

print("Escalation done")