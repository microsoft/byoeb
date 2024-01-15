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

reminder_message = f"You can change the language using the options below."
title = f"Options"

lang_prompts = {"en": reminder_message, "en_title": title, "en_yes": "Yes", "en_no": "No"}

languages = ["hi", "kn", "ta", "te"]

logger = LoggingDatabase(config)

for lang in languages:
    message_source = azure_translate.translate_text(
        input_text=reminder_message,
        source_language="en",
        target_language=lang,
        logger=logger,
    )
    title_source = azure_translate.translate_text(
        input_text=title, source_language="en", target_language=lang, logger=logger
    )
    yes_source = azure_translate.translate_text(
        input_text="Yes", source_language="en", target_language=lang, logger=logger
    )
    no_source = azure_translate.translate_text(
        input_text="No", source_language="en", target_language=lang, logger=logger
    )
    lang_prompts[lang] = str(message_source)
    lang_prompts[lang + "_title"] = str(title_source)
    lang_prompts[lang + "_yes"] = str(yes_source)
    lang_prompts[lang + "_no"] = str(no_source)

os.makedirs(os.path.join(os.environ["APP_PATH"], os.environ["DATA_PATH"], "onboarding"), exist_ok=True)
save_path = os.path.join(os.environ["APP_PATH"], os.environ["DATA_PATH"], "onboarding/language_prompts.json")
with open(save_path, "w") as fp:
    json.dump(lang_prompts, fp)
