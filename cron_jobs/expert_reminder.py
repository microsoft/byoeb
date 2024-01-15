import os
import yaml
import datetime

import sys
sys.path.append(os.environ["APP_PATH"] + "/src")

from conversation_database import LongTermDatabase, LoggingDatabase
from messenger.whatsapp import WhatsappMessenger



with open(os.path.join(os.environ["APP_PATH"], "config.yaml")) as file:
    config = yaml.load(file, Loader=yaml.FullLoader)

template_name="expert_reminder"
language="en"


long_term_db = LongTermDatabase(config)
logger = LoggingDatabase(config)
expert_list = []
for expert in config["EXPERTS"]:
    expert_list.append(long_term_db.get_list_of(expert+"_whatsapp_id"))

messenger = WhatsappMessenger(config, logger)


for whatsapp_id in expert_list:
    activity = list(logger.collection.find({"sender_id": whatsapp_id}))
    if len(activity) and (
        datetime.datetime.now() - activity[-1]["timestamp"]
    ) > datetime.timedelta(hours=0):
        continue
    try:
        print("Sending message to ", whatsapp_id)
        messenger.send_template(
            whatsapp_id, template_name, language, None
        )
    except:
        continue

print("Sent reminders to experts")

