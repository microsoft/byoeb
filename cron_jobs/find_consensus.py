import datetime
import sys
import yaml
import json
import os

local_path = os.environ["APP_PATH"]
with open(local_path + "/config.yaml") as file:
    config = yaml.load(file, Loader=yaml.FullLoader)

sys.path.append(local_path.strip() + "/src")


from database import UserDB, UserConvDB, BotConvDB, ExpertConvDB, UserRelationDB


from messenger import WhatsappMessenger
from responder import WhatsappResponder
from conversation_database import (
    LoggingDatabase
)

import subprocess
from utils import get_llm_response, remove_extra_voice_files

MIN_CONSENSUS_RESPONSES = 3

userdb = UserDB(config)
user_conv_db = UserConvDB(config)
bot_conv_db = BotConvDB(config)
expert_conv_db = ExpertConvDB(config)

responder = WhatsappResponder(config)

import pandas as pd
from tqdm import tqdm

logger = LoggingDatabase(config)


to_ts = datetime.datetime.now() - datetime.timedelta(hours=0)
from_ts = datetime.datetime.now() - datetime.timedelta(days=10)

list_cursor = user_conv_db.get_all_unresolved(from_ts, to_ts)

df = pd.DataFrame(list(list_cursor))

consensus_prompt_path = os.path.join(local_path, os.environ['DATA_PATH'], "consensus_prompt.txt")

with open(consensus_prompt_path, "r") as f:
    consensus_prompt = f.read()

# print(consensus_prompt)

for index, row in tqdm(df.iterrows()):

    transaction_message_id = row["message_id"]
    all_expert_responses = expert_conv_db.get_from_transaction_message_id(transaction_message_id, "consensus_response")

    if len(all_expert_responses) < MIN_CONSENSUS_RESPONSES:
        continue

    expert_responses = [response["message"] for response in all_expert_responses]

    prompt = [
        {"role": "system", "content": str(consensus_prompt)},
    ]

    query_prompt = f'''
    Please find the consensus for the following input:
    Query: {row["message_english"]}
    Experts' Responses: [{", ".join(expert_responses)}]
    Share the output in a json format {{"answer": "xxx", "explanation": "xxx", "voting": "xxx"}}, do not include anything else.
    '''

    prompt.append({"role": "user", "content": str(query_prompt)})

    
    


    response = get_llm_response(prompt)

    print(response)
    response = json.loads(response)
    if response['answer'] == 'Consensus not reached.':
        continue
    
    answer = response['answer']
    user_row_lt = userdb.get_from_user_id(row["user_id"])

    
    if row["message_type"] == "audio":
        corrected_audio_loc = "corrected_audio.wav"
        remove_extra_voice_files(
            corrected_audio_loc, corrected_audio_loc[:-3] + ".aac"
        )
        answer_source = responder.azure_translate.text_translate_speech(
            answer, user_row_lt['user_language'] + "-IN", corrected_audio_loc, logger
        )

        updated_msg_id = responder.messenger.send_message(
            user_row_lt['whatsapp_id'],
            answer_source,
            row["message_id"],
        )

        subprocess.run(
            [
                "ffmpeg",
                "-i",
                corrected_audio_loc,
                "-codec:a",
                "aac",
                corrected_audio_loc[:-3] + ".aac",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        updated_audio_msg_id = responder.messenger.send_audio(
            corrected_audio_loc[:-3] + ".aac",
            user_row_lt['whatsapp_id'],
            row["message_id"]
        )
        remove_extra_voice_files(
            corrected_audio_loc, corrected_audio_loc[:-3] + ".aac"
        )
    else:
        answer_source = responder.azure_translate.translate_text(
            answer, "en", user_row_lt['user_language'], logger
        )
        updated_msg_id = responder.messenger.send_message(
            user_row_lt['whatsapp_id'],
            answer_source,
            row["message_id"],
        )
        updated_audio_msg_id = None
    
    bot_conv_db.insert_row(
        receiver_id=user_row_lt['user_id'],
        message_type="query_consensus_response",
        message_id=updated_msg_id,
        audio_message_id=updated_audio_msg_id,
        message_source_lang=answer_source,
        message_language=user_row_lt['user_language'],
        message_english=answer,
        reply_id=row["message_id"],
        citations="expert_consensus",
        message_timestamp=datetime.datetime.now(),
        transaction_message_id=row["message_id"],
    )

    user_conv_db.mark_resolved(row["message_id"])
    print("Marking resolved", row["message_id"])





