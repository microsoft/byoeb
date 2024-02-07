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

title = "What to do next?"
list_title = "Related questions"
questions = config['SUGGESTION_QUESTIONS']
data = {"title": title, "list_title": list_title, "questions": questions}
onboard_ques = {"en": data}
languages = ["hi", "kn", "ta", "te"]

logger = LoggingDatabase(config)

# store onboard questions in all langs in json file


for lang in languages:
    current_title = azure_translate.translate_text(title, "en", lang, logger)
    current_list_title = azure_translate.translate_text(list_title, "en", lang, logger)
    current_questions = []
    for question in questions:
        message_source = azure_translate.translate_text(
            input_text=question,
            source_language="en",
            target_language=lang,
            logger=logger,
        )
        current_questions.append(str(message_source))
    onboard_ques[lang] = {
        "title": current_title,
        "list_title": current_list_title,
        "questions": current_questions,
    }

os.makedirs(os.path.join(os.environ["APP_PATH"], os.environ["DATA_PATH"], "onboarding"), exist_ok=True)
save_path = os.path.join(os.environ["APP_PATH"], os.environ["DATA_PATH"], "onboarding/suggestion_questions.json")

with open(save_path, "w") as fp:
    json.dump(onboard_ques, fp)
