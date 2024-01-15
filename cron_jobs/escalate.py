import datetime
import sys
import yaml

import os

local_path = os.environ["APP_PATH"]
with open(local_path + "/config.yaml") as file:
    config = yaml.load(file, Loader=yaml.FullLoader)

sys.path.append(local_path.strip() + "/src")
from messenger.whatsapp import WhatsappMessenger
from conversation_database import (
    ConversationDatabase,
    LongTermDatabase,
    LoggingDatabase,
)
import pandas as pd
from tqdm import tqdm

database = ConversationDatabase(config)
long_term_db = LongTermDatabase(config)
logger = LoggingDatabase(config)

messenger = WhatsappMessenger(config, logger)

to_ts = datetime.datetime.now() - datetime.timedelta(hours=3)
from_ts = datetime.datetime.now() - datetime.timedelta(hours=6)
list_cursor = database.get_rows_timestamp("timestamp", from_ts, to_ts)
df_hour = pd.DataFrame(list_cursor)

if df_hour.empty:
    print("No new messages in the hour")
    sys.exit()

df_hour.reset_index(drop=True, inplace=True)

for i in tqdm(range(len(df_hour))):
    if (
        df_hour.loc[i, "is_correct"] == True
        or df_hour.loc[i, "is_correct"] == False
        or df_hour.loc[i, "query_type"] == "small-talk"
    ):
        continue
    if df_hour.loc[i, "poll_escalated_id"]:
        continue
    messenger.send_correction_poll_expert(
        database, long_term_db, df_hour.loc[i, "_id"], escalation=True
    )

print("Escalation done")