from conversation_database import LoggingDatabase
import json
import os
from azure_language_tools import translator
from messenger import WhatsappMessenger
from database import UserDB


def onboard_template(config: dict, logger: LoggingDatabase, data_row: dict) -> None:
    print("Onboarding template")

    messenger = WhatsappMessenger(config, logger)

    for user in config['USERS']:
        if data_row.get(user+'_whatsapp_id', None) is not None:
            lang = data_row.get(user+'_language', 'en')
            messenger.send_template(
                data_row[user+'_whatsapp_id'],
                'onboard_user',
                lang,
            )
    
    for expert in config['EXPERTS']:
        if data_row.get(expert+'_whatsapp_id', None) is not None:
            lang = data_row.get(expert+'_language', 'en')
            messenger.send_template(
                data_row[expert+'_whatsapp_id'],
                'onboard_expert',
                lang,
            )

def onboar_medics_template(
    config: dict,
    logger: LoggingDatabase,
    to_number: str,
    ) -> None:
    messenger = WhatsappMessenger(config, logger)
    try:
        messenger.send_template(to_number, 'onboard_cataractbot', 'en', logger)
        messenger.send_template(to_number, 'lang_selection_blr', 'en', logger)
        print('Template sent to user')
    except Exception as e:
        print(e)
        print('Error in sending template to user')


def onboard_wa_helper(
    config: dict,
    logger: LoggingDatabase,
    to_number: str,
    role: str,
    lang: str,
    user_id: str,
    user_db: UserDB,
) -> None:
    messenger = WhatsappMessenger(config, logger)
    welcome_messages = json.load(
        open(
            os.path.join(os.environ['APP_PATH'], os.environ['DATA_PATH'],"onboarding/welcome_messages.json"),
        )
    )
    language_prompts = json.load(
        open(
            os.path.join(os.environ['APP_PATH'], os.environ['DATA_PATH'],"onboarding/language_prompts.json"),
        )
    )
    suggestion_questions = json.load(
        open(
            os.path.join(os.environ['APP_PATH'], os.environ['DATA_PATH'],"onboarding/suggestion_questions.json"),
        )
    )

    if role in config["USERS"]:
        for message in welcome_messages["users"][lang]:
            messenger.send_message(to_number, message)
        audio_file = os.path.join(os.environ['APP_PATH'], os.environ['DATA_PATH'],f"onboarding/welcome_messages_users_{lang}.aac")
        messenger.send_audio(audio_file, to_number)
        user_db.add_or_update_related_qns(user_id, suggestion_questions["en"]["questions"])
        title, questions, list_title = (
            suggestion_questions[lang]["title"],
            suggestion_questions[lang]["questions"],
            suggestion_questions[lang]["list_title"],
        )

        messenger.send_suggestions(to_number, title, list_title, questions)
        return

    if role in config["EXPERTS"]:
        for message in welcome_messages["experts"][lang]:
            messenger.send_message(to_number, message)
        audio_file = os.path.join(os.environ['APP_PATH'], os.environ['DATA_PATH'],f"onboarding/welcome_messages_experts_{lang}.aac")
        messenger.send_audio(audio_file, to_number)
        return

    return