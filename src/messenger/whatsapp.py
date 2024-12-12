import sys
import os
import json
from dataclasses import asdict, dataclass
from abc import ABC, abstractmethod
from typing import List

sys.path.append(os.path.dirname(__file__))
src_path = os.path.join(os.environ["APP_PATH"], "src")

import requests
from conversation_database import (
    ConversationDatabase,
    LongTermDatabase,
    LoggingDatabase,
)
from knowledge_base import KnowledgeBase
from datetime import datetime
import numpy as np
from azure_language_tools import translator
from utils import remove_extra_voice_files
import subprocess
from messenger.base import BaseMessenger

@dataclass
class TemplateParameters():   
    text: str
    type: str = "text"

class WhatsappMessenger(BaseMessenger):
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        
        self.users_types = self.config["USERS"]
        self.experts_types = []
        self.categories = []
        self.category_to_expert = {}
        for expert in self.config["EXPERTS"]:
            self.experts_types.append(self.config["EXPERTS"])
            self.categories.append(self.config["EXPERTS"][expert])
            self.category_to_expert[self.config["EXPERTS"][expert]] = expert


    def send_message(
        self,
        to_number: str,
        msg_body: str,
        reply_to_msg_id: str = None,
    ):
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "text": {"body": msg_body},
        }

        if reply_to_msg_id is not None:
            payload["context"] = {"message_id": reply_to_msg_id}

        headers = {
            "Authorization": "Bearer " + os.environ["WHATSAPP_TOKEN"].strip(),
            "Content-Type": "application/json",
        }

        url = (
            "https://graph.facebook.com/v12.0/"
            + os.environ["PHONE_NUMBER_ID"]
            + "/messages"
        )
        msg_output = requests.post(url, json=payload, headers=headers)

        print("Message output: ", msg_output.json())
        try:
            msg_id = msg_output.json()["messages"][0]["id"]
        except KeyError:
            print(msg_output.json())
            raise Exception("Error in sending message")

        self.logger.add_log(
            sender_id="bot",
            receiver_id=to_number,
            message_id=msg_id,
            action_type="send_message",
            details={"text": msg_body, "reply_to": reply_to_msg_id},
            timestamp=datetime.now(),
        )

        return msg_id
    
    def send_message_with_options(
        self,
        to_number: str,
        msg_body: str,
        options_ids: list,
        options_title: list,
        reply_to_msg_id: str = None,
    ):
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": msg_body},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": option_id, "title": option}}
                        for option_id, option in zip(options_ids, options_title)
                    ]
                },
            },
        }

        if reply_to_msg_id is not None:
            payload["context"] = {"message_id": reply_to_msg_id}

        headers = {
            "Authorization": "Bearer " + os.environ["WHATSAPP_TOKEN"].strip(),
            "Content-Type": "application/json",
        }

        url = (
            "https://graph.facebook.com/v17.0/"
            + os.environ["PHONE_NUMBER_ID"]
            + "/messages"
        )

        msg_output = requests.post(url, json=payload, headers=headers)
        print(msg_output.json())
        msg_id = msg_output.json()["messages"][0]["id"]

        self.logger.add_log(
            sender_id="bot",
            receiver_id=to_number,
            message_id=msg_id,
            action_type="send_message",
            details={"text": msg_body, "options": options_title, "reply_to": reply_to_msg_id},
            timestamp=datetime.now(),
        )

        return msg_id

    def send_reaction(
        self,
        to_number: str,
        reply_to_msg_id: str = None,
        emoji: str = "👍",
    ):
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "reaction",
            "reaction": {"message_id": reply_to_msg_id, "emoji": emoji},
        }

        headers = {
            "Authorization": "Bearer " + os.environ["WHATSAPP_TOKEN"].strip(),
            "Content-Type": "application/json",
        }
        url = (
            "https://graph.facebook.com/v17.0/"
            + os.environ["PHONE_NUMBER_ID"]
            + "/messages"
        )

        msg_output = requests.post(url, json=payload, headers=headers)
        try:
            msg_id = msg_output.json()["messages"][0]["id"]
        except KeyError:
            print(msg_output.json())
            raise Exception("Error in sending reaction")
        self.logger.add_log(
            sender_id="bot",
            receiver_id=to_number,
            message_id=msg_id,
            action_type="send_reaction",
            details={"emoji": emoji, "reply_to": reply_to_msg_id},
            timestamp=datetime.now(),
        )

        return

    def send_poll(
        self,
        to_number: str,
        poll_string: str,
        reply_to_msg_id: str = None,
        poll_id: str = None,
    ):
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": poll_string},
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {"id": poll_id + "_YES", "title": "Yes"},
                        },
                        {
                            "type": "reply",
                            "reply": {"id": poll_id + "_NO", "title": "No"},
                        }
                    ]
                },
            },
        }

        if reply_to_msg_id is not None:
            payload["context"] = {"message_id": reply_to_msg_id}

        headers = {
            "Authorization": "Bearer " + os.environ["WHATSAPP_TOKEN"].strip(),
            "Content-Type": "application/json",
        }
        url = (
            "https://graph.facebook.com/v17.0/"
            + os.environ["PHONE_NUMBER_ID"]
            + "/messages"
        )

        msg_output = requests.post(url, json=payload, headers=headers)

        try:
            msg_id = msg_output.json()["messages"][0]["id"]
        except KeyError:
            print(msg_output.json())
            return "Error in sending poll"
        
        self.logger.add_log(
            sender_id="bot",
            receiver_id=to_number,
            message_id=msg_id,
            action_type="send_poll",
            details={
                "text": poll_string,
                "reply_to": reply_to_msg_id,
                "options": ["Yes", "No"],
            },
            timestamp=datetime.now(),
        )

        self.send_reaction(to_number, msg_id, "\u2753")

        return msg_id

    def send_language_poll(
        self,
        to_number: str,
        poll_string: str,
        title: str,
    ):
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": poll_string},
                "action": {
                    "button": title,
                    "sections": [
                        {
                            "title": "Language Selection",
                            "rows": [
                                {"id": "LANG_ENG", "title": "English"},
                                {"id": "LANG_HIN", "title": "हिंदी"},
                                {"id": "LANG_KNA", "title": "ಕನ್ನಡ"},
                                {"id": "LANG_TAM", "title": "தமிழ்"},
                                {"id": "LANG_TEL", "title": "తెలుగు"},
                            ],
                        }
                    ],
                },
            },
        }

        headers = {
            "Authorization": "Bearer " + os.environ["WHATSAPP_TOKEN"].strip(),
            "Content-Type": "application/json",
        }
        url = (
            "https://graph.facebook.com/v17.0/"
            + os.environ["PHONE_NUMBER_ID"]
            + "/messages"
        )

        msg_output = requests.post(url, json=payload, headers=headers)
        msg_id = msg_output.json()["messages"][0]["id"]
        self.logger.add_log(
            sender_id="bot",
            receiver_id=to_number,
            message_id=msg_id,
            action_type="send_poll",
            details={
                "text": poll_string,
                "reply_to": None,
                "options": ["English", "हिंदी", "ಕನ್ನಡ", "தமிழ்", "తెలుగు"],
            },
            timestamp=datetime.now(),
        )

        return msg_id

    def send_suggestions(
        self,
        to_number: str,
        text_poll: str = None,
        list_title: str = None,
        questions: list = None,
        reply_to_msg_id: str = None,
    ):
        if questions is None or questions == []:
            return
        final_questions_list = []

        for i, question in enumerate(questions):
            if len(question) > 72:
                question = question[:69] + "..."
            final_questions_list.append(
                {"id": "QUESTION_" + str(i + 1), "title": " ", "description": question}
            )

        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": text_poll},
                "action": {
                    "button": list_title,
                    "sections": [
                        {"title": list_title, "rows": final_questions_list},
                    ],
                },
            },
        }

        if reply_to_msg_id is not None:
            payload["context"] = {"message_id": reply_to_msg_id}

        headers = {
            "Authorization": "Bearer " + os.environ["WHATSAPP_TOKEN"].strip(),
            "Content-Type": "application/json",
        }
        url = (
            "https://graph.facebook.com/v17.0/"
            + os.environ["PHONE_NUMBER_ID"]
            + "/messages"
        )
        msg_output = requests.post(url, json=payload, headers=headers)
        try:    
            msg_id = msg_output.json()["messages"][0]["id"]
        except KeyError:
            print(msg_output.json())
            raise Exception("Error in sending suggestions")

        self.logger.add_log(
            sender_id="bot",
            receiver_id=to_number,
            message_id=msg_id,
            action_type="send_suggestions",
            details={"text": text_poll, "suggestions": questions},
            timestamp=datetime.now(),
        )

        return msg_id

    def send_template(
        self,
        to_number: str,
        template_name: str,
        language: str,
        text_parameters: List[str] = [],
        reply_to_msg_id: str = None,
    ):
        parameters_list = []
        for text_param in text_parameters:
            parameters_list.append(
                TemplateParameters(
                    text=text_param
                )
            )
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language,
                },
            },
        }

        if reply_to_msg_id is not None:
            payload["context"] = {"message_id": reply_to_msg_id}
            
        if len(parameters_list) != 0:
            print("Has parameters")
            payload["template"]["components"] = [{
                "type": "body"
            }]
            json_object = json.dumps([asdict(obj) for obj in parameters_list])
            payload["template"]["components"][0]["parameters"] = json.loads(json_object)

        headers = {
            "Authorization": "Bearer " + os.environ["WHATSAPP_TOKEN"].strip(),
            "Content-Type": "application/json",
        }

        url = (
            "https://graph.facebook.com/v17.0/"
            + os.environ["PHONE_NUMBER_ID"]
            + "/messages"
        )
        msg_output = requests.post(url, json=payload, headers=headers)

        print("Message output: ", msg_output.json())
        msg_id = msg_output.json()["messages"][0]["id"]

        self.logger.add_log(
            sender_id="bot",
            receiver_id=to_number,
            message_id=msg_id,
            action_type="send_message",
            details={"text": template_name, "reply_to": reply_to_msg_id},
            timestamp=datetime.now(),
        )

        return msg_id

    def download_audio(
        self,
        msg_object: dict,
        audio_file: str,
    ) -> str:
        audio_id = msg_object["audio"]["id"]

        url = f"https://graph.facebook.com/v17.0/{audio_id}/"

        headers = {"Authorization": f"Bearer {os.environ['WHATSAPP_TOKEN'].strip()}"}

        response = requests.get(url, headers=headers)
        data = response.json()

        print("Audio output: ", data)
        data_url = data["url"]

        output_file = audio_file
        headers = {"Authorization": f"Bearer {os.environ['WHATSAPP_TOKEN'].strip()}"}
        response = requests.get(data_url, headers=headers)

        # Save the response content to a file
        with open(output_file, "wb") as file:
            file.write(response.content)

        print(f"Media file saved as {output_file}")

    def send_audio(
        self,
        audio_output_file: str,
        to_number: str,
        reply_to_msg_id: str = None,
    ) -> str:
        url = (
            "https://graph.facebook.com/v15.0/"
            + os.environ["PHONE_NUMBER_ID"]
            + "/media"
        )
        payload = {"messaging_product": "whatsapp"}
        

        if audio_output_file.endswith(".aac"):
            files = [
                ("file", (audio_output_file, open(audio_output_file, "rb"), "audio/aac"))
            ]
        elif audio_output_file.endswith(".ogg"):
            files = [
                ("file", (audio_output_file, open(audio_output_file, "rb"), "audio/ogg"))
            ]

        headers = {
            "Authorization": f"Bearer {os.environ['WHATSAPP_TOKEN'].strip()}",
        }
        response = requests.request(
            "POST", url, headers=headers, data=payload, files=files
        )

        data = response.json()
        print("Audio data: ", data)
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "audio",
            "audio": {"id": data["id"]},
        }

        if reply_to_msg_id is not None:
            payload["context"]: {"message_id": reply_to_msg_id}
        
        headers = {
            "Authorization": "Bearer " + os.environ["WHATSAPP_TOKEN"].strip(),
            "Content-Type": "application/json",
        }
        url = (
            "https://graph.facebook.com/v17.0/"
            + os.environ["PHONE_NUMBER_ID"]
            + "/messages"
        )

        msg_output = requests.post(url, json=payload, headers=headers)
        print("msg output: ", msg_output.json())
        msg_id = msg_output.json()["messages"][0]["id"]

        return msg_id
