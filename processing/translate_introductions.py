import os
import sys
local_path = os.path.join(os.environ['APP_PATH'], 'src')
sys.path.append(local_path)
from azure_language_tools import translator
import json
from conversation_database import LoggingDatabase
import yaml

config_path = os.path.join(os.environ['APP_PATH'], 'config.yaml')
with open(config_path) as file:
    config = yaml.load(file, Loader=yaml.FullLoader)

azure_translate = translator()

welcome_messages_users = config['WELCOME_MESSAGES']['USERS']
welcome_messages_experts = config['WELCOME_MESSAGES']['EXPERTS']

welcome_messages = {
    "users": {"en": welcome_messages_users},
    "experts": {"en": welcome_messages_experts},
}

languages = ["hi", "kn", "ta", "te"]

for lang in languages:
    welcome_messages["users"][lang] = []

logger = LoggingDatabase(config)

for lang in languages:
    for message in welcome_messages_users:
        message_source = azure_translate.translate_text(
            input_text=message,
            source_language="en",
            target_language=lang,
            logger=logger,
        )
        welcome_messages["users"][lang].append(str(message_source))

os.makedirs(os.path.join(os.environ["APP_PATH"], os.environ['DATA_PATH'], "onboarding"), exist_ok=True)

save_path = os.path.join(os.environ["APP_PATH"], os.environ['DATA_PATH'], "onboarding/welcome_messages.json")
with open(save_path, "w") as fp:
    json.dump(welcome_messages, fp)
