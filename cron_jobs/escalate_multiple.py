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

responder = WhatsappResponder(config)

import pandas as pd
from tqdm import tqdm

logger = LoggingDatabase(config)


to_ts = datetime.datetime.now() - datetime.timedelta(hours=0)
from_ts = datetime.datetime.now() - datetime.timedelta(days=1)

list_cursor = user_conv_db.get_all_unresolved(from_ts, to_ts)

df = pd.DataFrame(list_cursor)
df = df[df['query_type'] != 'small-talk']
df.reset_index(drop=True, inplace=True)

category_to_expert = {}

for expert in config["EXPERTS"]:
    category_to_expert[config["EXPERTS"][expert]] = expert

for i, row in tqdm(df.iterrows()):
    print(row.keys())
    # print(row['message_id'], row['message_english'])
    try:
    # get x numbers of experts randomly
        experts = userdb.get_random_expert(category_to_expert[df.loc[i, "query_type"]], NUM_EXPERTS)

        # print(experts)
        
        for expert in experts:
            responder.send_query_expert(expert, row)
    except Exception as e:
        print(e)

    

print("Escalation done")