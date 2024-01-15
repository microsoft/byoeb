import psutil
import yaml

import os

print("Code started running")
local_path = os.environ["APP_PATH"]
import sys

sys.path.append(local_path + "/src")
from knowledge_base import KnowledgeBase
from conversation_database import LoggingDatabase
import pandas as pd
import utils
from tqdm import tqdm
from datetime import datetime

with open(os.path.join(local_path, "config.yaml")) as file:
    config = yaml.load(file, Loader=yaml.FullLoader)

RANGE_NAME = "KB_Update"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = config["SPREADSHEET_ID"].strip()


data = utils.pull_sheet_data(SCOPES, SPREADSHEET_ID, RANGE_NAME, local_path)
df_previous = pd.DataFrame(data[1:], columns=data[0])
print(df_previous.columns)
df_previous["To Update Knowledge Base (YES/NO)"] = df_previous[
    "To Update Knowledge Base (YES/NO)"
].str.upper()
df_not_updated = df_previous[
    df_previous["To Update Knowledge Base (YES/NO)"].isin(["YES", "NO"]) == False
]
df_updated = df_previous[
    df_previous["To Update Knowledge Base (YES/NO)"].isin(["YES"]) == True
]
df_updated.reset_index(drop=True, inplace=True)
df_deleted = df_previous[
    df_previous["To Update Knowledge Base (YES/NO)"].isin(["NO"]) == True
]
df_deleted.reset_index(drop=True, inplace=True)
os.makedirs(os.path.join(local_path, os.environ['DATA_PATH'], "kb_update_raw"), exist_ok=True)
open(os.path.join(local_path, os.environ['DATA_PATH'], "kb_update_raw/KB Updated.txt"), "w").close()
myfile = open(os.path.join(local_path, os.environ['DATA_PATH'], "kb_update_raw/KB Updated.txt"), "a")
rawfile = open(os.path.join(local_path, os.environ['DATA_PATH'], "raw_documents/KB Updated.txt"), "a")

logger = LoggingDatabase(config)

for i in tqdm(range(len(df_deleted))):
    query = df_deleted.loc[i, "Question"]
    response = df_deleted.loc[i, "Final Answer To Be Updated in KB"]
    date = df_deleted.loc[i, "Date"]
    logger.add_log(
        sender_id="KB updater",
        receiver_id="Bot",
        message_id=None,
        action_type="Not Updating KnowledgeBase",
        details={
            "date": date,
            "query": query,
            "response": response,
            "To Update KB": "NO",
        },
        timestamp=datetime.now(),
    )

if df_updated.empty:
    print("No new updates to KB")

for i in tqdm(range(len(df_updated))):
    print(repr(df_updated.columns))
    query = df_updated.loc[i, "Question"]
    updated_response = df_updated.loc[i, "Final Answer To Be Updated in KB"]
    date = df_updated.loc[i, "Date"]
    logger.add_log(
        sender_id="KB updater",
        receiver_id="Bot",
        message_id=None,
        action_type="Updating KnowledgeBase",
        details={
            "date": date,
            "query": query,
            "updated_response": updated_response,
            "To Update KB": "YES",
        },
        timestamp=datetime.now(),
    )
    myfile.write(f"* {query.strip()}\n{updated_response.strip()}\n\n")
    rawfile.write(f"* {query.strip()}\n{updated_response.strip()}\n\n")

myfile.close()
rawfile.close()

if not df_updated.empty:
    knowledge_base = KnowledgeBase(config)
    knowledge_base.update_kb_wa()
    print("KB updated successfully")

utils.delete_all_rows(SCOPES, SPREADSHEET_ID, RANGE_NAME, local_path)
utils.add_rows(SCOPES, SPREADSHEET_ID, RANGE_NAME, df_not_updated, local_path)