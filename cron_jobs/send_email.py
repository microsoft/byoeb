import smtplib
import pandas as pd
import yaml
import os
import datetime
import sys

local_path = os.environ["APP_PATH"]

sys.path.append(local_path + "/src")
from conversation_database import (
    ConversationDatabase,
    LongTermDatabase,
    LoggingDatabase,
)

import utils


with open(os.path.join(local_path, "config.yaml")) as file:
    config = yaml.load(file, Loader=yaml.FullLoader)

RANGE_NAME = "KB_Update"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = config["SPREADSHEET_ID"].strip()

database = ConversationDatabase(config)
long_term_db = LongTermDatabase(config)
logger = LoggingDatabase(config)

to_ts = datetime.datetime.now()
from_ts = to_ts - datetime.timedelta(days=10)
list_cursor = database.get_rows_timestamp("timestamp_correction", from_ts, to_ts)
df_last_day = pd.DataFrame(list_cursor)
if df_last_day.empty:
    print("No new messages in the last day")
    sys.exit()
print("df_last_day columns: ", df_last_day.columns)
df_last_day = df_last_day[
    [
        "query",
        "response",
        "correction",
        "updated_response",
        "user_id",
        "query_type",
        "answered_by",
    ]
]
date = datetime.datetime.now().strftime("%d-%m-%Y")
category_to_expert = {}
for expert in config["EXPERTS"]:
        category_to_expert[config["EXPERTS"][expert]] = expert

for i in range(len(df_last_day)):
    query_type_i = df_last_day.loc[i, "query_type"]
    print(query_type_i)
    if query_type_i not in category_to_expert:
        #delete row
        df_last_day.drop(i, inplace=True)
        continue
    print(category_to_expert[query_type_i])
    row_lt = long_term_db.get_rows(
        df_last_day.loc[i, "user_id"], "user_id"
    )[0]
    df_last_day.loc[i, "user_id"] = row_lt["user_id"]

    ans_num = df_last_day.loc[i, "answered_by"]
    logger.add_log(
        sender_id="bot",
        receiver_id="kb updater",
        message_id=None,
        action_type="Sending question for kb updation",
        details={
            "query": df_last_day.loc[i, "query"],
            "response": df_last_day.loc[i, "updated_response"],
            "date": date,
        },
        timestamp=datetime.datetime.now(),
    )
    
    expert = category_to_expert[query_type_i]
    if ans_num == config["ESCALATION"][expert]['whatsapp_id']:
        df_last_day.loc[i, "correction_by"] = config["ESCALATION"][expert]['name']
    else:
        df_last_day.loc[i, "correction_by"] = row_lt[expert+"_name"]
    
if df_last_day.empty:
    print("No new messages in the last day")
    sys.exit()

df_last_day["date"] = datetime.datetime.now().strftime("%d-%m-%Y")
print(df_last_day)
df_last_day = df_last_day[
    [
        "date",
        "user_id",
        "query",
        "response",
        "correction",
        "correction_by",
        "updated_response",
    ]
]
df_last_day.columns = [
    "Date",
    "User ID",
    "Question",
    "Bot's Answer",
    "Correction",
    "Correction By",
    "Final Answer",
]
df_last_day["To Update Knowledge Base (YES/NO)"] = "?"

utils.append_rows(SCOPES, SPREADSHEET_ID, RANGE_NAME, df_last_day, local_path)

li = config["EMAIL_LIST"]
link_to_sheet = config["SHEET_LINK"].strip()
date_today = datetime.datetime.now().strftime("%d-%m-%Y")
for dest in li:
    s = smtplib.SMTP("smtp.gmail.com", 587)
    s.starttls()
    s.login(config["EMAIL_ID"], config["EMAIL_PASS"].strip())
    message = f"Subject: BYOeB log {date_today}. \n\nHello team, \nHere is a link to today's BYOeB log: {link_to_sheet}. \n\nPlease update the column 'To Update Knowledge Base' with a YES/NO depending upon the expert's correction. \n\n\
Best regards, \BYOeB Bot team."
    s.sendmail(config["EMAIL_ID"], dest, message)
    print(dest, li)
    s.quit()
