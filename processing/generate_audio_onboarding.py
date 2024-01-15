import os
import sys
local_path = os.path.join(os.environ['APP_PATH'], 'src')
sys.path.append(local_path)
from azure_language_tools import translator
import json
import subprocess

languages = ["en", "hi", "kn", "ta", "te"]
roles = ["users", "experts"]

role = "experts"
azure_translate = translator()
welcome_messages = json.load(
    open(
        os.path.join(os.environ["APP_PATH"], os.environ["DATA_PATH"], "onboarding/welcome_messages.json")
    )
)

final_message = ""
for message in welcome_messages[role]["en"]:
    final_message += message + "\n\n"

audio_path = (
    "onboarding/welcome_messages_"
    + role
    + "_"
    + "en"
    + ".wav"
)
audio_path = os.path.join(os.environ["APP_PATH"], os.environ["DATA_PATH"], audio_path)
    
azure_translate.text_to_speech(final_message, "en-IN", audio_path)

subprocess.run(
    ["ffmpeg", "-y", "-i", audio_path, "-codec:a", "aac", audio_path[:-3] + "aac"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)

for language in languages:
    role = "users"
    final_message = ""
    for message in welcome_messages[role][language]:
        final_message += message + "\n\n"

    audio_path = (
        "onboarding/welcome_messages_"
        + role
        + "_"
        + language
        + ".wav"
    )
    audio_path = os.path.join(os.environ["APP_PATH"], os.environ["DATA_PATH"], audio_path)
    azure_translate.text_to_speech(final_message, language + "-IN", audio_path)

    subprocess.run(
        ["ffmpeg", "-y", "-i", audio_path, "-codec:a", "aac", audio_path[:-3] + "aac"],
        )
