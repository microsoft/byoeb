
import yaml
import os

local_path = os.environ["APP_PATH"]
with open(os.path.join(local_path, "config.yaml")) as file:
    config = yaml.load(file, Loader=yaml.FullLoader)
import sys

sys.path.append(local_path + "/src")

from conversation_database import LongTermDatabase, LoggingDatabase
from messenger.whatsapp import WhatsappMessenger
import os
import json
import datetime

template_name = "reminder_cataractbot"

long_term_db = LongTermDatabase(config)
logger = LoggingDatabase(config)
messenger = WhatsappMessenger(config, logger)

print("Date: ", datetime.datetime.now())

all_user_list = []
all_user_language = []
all_user_expiration = []

for user in config["USERS"]:
    user_list = long_term_db.get_list_of_multiple_columns([user+"_whatsapp_id", user+"_language", "is_expired"])
    all_user_list = all_user_list + user_list[user+"_whatsapp_id"]
    all_user_language = all_user_language + user_list[user+"_language"]
    all_user_expiration = all_user_expiration + user_list["is_expired"]



for user_whatsapp_id, user_language, expired in zip(all_user_list, all_user_language, all_user_expiration):
    
    activity = list(logger.collection.find({"sender_id": user_whatsapp_id}))

    if expired or (len(activity) and (
        datetime.datetime.now() - activity[-1]["timestamp"]
    ) < datetime.timedelta(hours=2)):
        continue
    

    try:
        print("Sending message to ", user_whatsapp_id)
        messenger.send_template(user_whatsapp_id, template_name, user_language, None)
    except:
        continue

print("Sent messages to patients and caregivers")
