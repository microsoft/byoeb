from typing import Any
from io import BytesIO

import os
from azure_language_tools import translator
import subprocess
from datetime import datetime
from azure.storage.blob import BlobServiceClient

import json
from knowledge_base import KnowledgeBase
from conversation_database import (
    ConversationDatabase,
    LongTermDatabase,
    LoggingDatabase,
)
from database import BaseDB, UserConvDB, BotConvDB, ExpertConvDB
from messenger.whatsapp import WhatsappMessenger
import utils
from onboard import onboard_wa_helper
from responder.base import BaseResponder


class WhatsappResponder(BaseResponder):
    def __init__(self, config):
        self.config = config
        self.knowledge_base = KnowledgeBase(config)
        # self.database = ConversationDatabase(config)
        self.long_term_db = LongTermDatabase(config)
        self.logger = LoggingDatabase(config)
        self.messenger = WhatsappMessenger(config, self.logger)
        self.azure_translate = translator()

        self.user_conv_db = UserConvDB(config)
        self.bot_conv_db = BotConvDB(config)
        self.expert_conv_db = ExpertConvDB(config)

        self.welcome_messages = json.load(
            open(os.path.join(os.environ['DATA_PATH'], "onboarding/welcome_messages.json"), "r")
        )
        self.language_prompts = json.load(
            open(os.path.join(os.environ['DATA_PATH'], "onboarding/language_prompts.json"), "r")
        )
        self.onboarding_questions = json.load(
            open(os.path.join(os.environ['DATA_PATH'], "onboarding/suggestion_questions.json"), "r")
        )
        self.yes_responses = [
            self.language_prompts[key]
            for key in self.language_prompts.keys()
            if key[-3:] == "yes"
        ]
        self.no_responses = [
            self.language_prompts[key]
            for key in self.language_prompts.keys()
            if key[-2:] == "no"
        ]


    def check_user_type(self, from_number):
        for user in self.config["USERS"]:
            rows = self.long_term_db.get_rows(from_number, user+"_whatsapp_id")
            print(user, rows)
            if len(rows) > 0:
                return user, rows[0]
            
        for expert in self.config["EXPERTS"]:
            rows = self.long_term_db.get_rows(from_number, expert+"_whatsapp_id")
            print(expert, rows)
            if len(rows) > 0:
                return expert, rows[0]
            
        return None, None

    def update_kb(self):
        self.knowledge_base = KnowledgeBase(self.config)

    def response(self, body):
        print("Entering response function")
        if (
            body.get("object")
            and body.get("entry")
            and body["entry"][0].get("changes")
            and body["entry"][0]["changes"][0].get("value")
            and body["entry"][0]["changes"][0]["value"].get("messages")
            and body["entry"][0]["changes"][0]["value"]["messages"][0]
        ):
            pass
        else:
            return

        msg_object = body["entry"][0]["changes"][0]["value"]["messages"][0]
        from_number = msg_object["from"]
        msg_id = msg_object["id"]
        msg_type = msg_object["type"]

        print("Message object: ", msg_object)


        

        # if msg_id in self.database.get_all_message_ids():
        #     print("Message already processed", datetime.now())
        #     return

        if self.user_conv_db.get_from_message_id(msg_id) or self.bot_conv_db.get_from_message_id(msg_id) or self.expert_conv_db.get_from_message_id(msg_id):
            print("Message already processed", datetime.now())
            return

        user_type, row_lt = self.check_user_type(from_number)
        print("User type: ", user_type, "Row: ", row_lt)
        if user_type is None:
            self.messenger.send_message(
                from_number,
                "Unknown User, Kindly fill the onboarding form",
                reply_to_msg_id=msg_id,
            )
            return

        if self.check_expiration(from_number, user_type, row_lt):
            return


        unsupported_types = ["image", "document", "video", "location", "contacts"]
        if msg_type in unsupported_types:
            self.handle_unsupported_msg_types(
                {"msg_object": msg_object, "from_number": from_number, "msg_id": msg_id}
            )
            return

        if msg_object.get("context", False) and msg_object["context"].get("id", False):
            reply_id = msg_object["context"]["id"]
            msg_log = self.logger.get_log_from_message_id(reply_id)[0]
            if (
                msg_log["details"]["text"] == "user_onboard"
                or msg_log["details"]["text"] == "expert_onboard"
            ):
                self.onboard_response(
                    {
                        "msg_object": msg_object,
                        "from_number": from_number,
                        "msg_id": msg_id,
                        "reply_id": reply_id,
                    }
                )
                return
            if msg_log["details"]["text"] == "expert_reminder":
                self.expert_reminder_response(
                    {
                        "msg_object": msg_object,
                        "from_number": from_number,
                        "msg_id": msg_id,
                        "reply_id": reply_id,
                    }
                )
                return


        user_type = self.get_user_type(from_number)

        if user_type in self.config["USERS"]:
            self.handle_response_user(
                {
                    "msg_object": msg_object,
                    "from_number": from_number,
                    "msg_id": msg_id,
                    "user_id": self.get_user_id(from_number),
                    "user_type": user_type,
                }
            )
        elif user_type in self.config["EXPERTS"]:
            self.handle_response_expert(
                {"msg_object": msg_object, "from_number": from_number, "msg_id": msg_id}
            )

        return

    def handle_unsupported_msg_types(self, data):
        # data is a dictionary that contains from_number, msg_id, msg_object
        print("Handling unsupported message types")
        msg_object = data["msg_object"]
        from_number = data["from_number"]
        msg_id = data["msg_id"]
        self.logger.add_log(
            sender_id=from_number,
            receiver_id="bot",
            message_id=msg_id,
            action_type="unsupported message format",
            details={"text": msg_object["type"], "reply_to": None},
            timestamp=datetime.now(),
        )
        text = "Sorry, this format is not supported right now, please send your queries as text/voice messages."
        lang = "en"
        for user in self.config["USERS"]:
            if from_number in self.long_term_db.get_list_of(user+"_whatsapp_id"):
                lang = self.long_term_db.get_rows(from_number, user+"_whatsapp_id")[0][
                    user + "_language"
                ]
        translated_text = self.azure_translate.translate_text(
            text, "en", lang, self.logger
        )
        self.messenger.send_message(
            from_number, translated_text, reply_to_msg_id=msg_id
        )
        return
    
    def get_user_id(self, from_number):
        for user in self.config["USERS"]:
            if from_number in self.long_term_db.get_list_of(user+"_whatsapp_id"):
                return self.long_term_db.get_rows(from_number, user+"_whatsapp_id")[0][
                    "user_id"
                ]
        return None

    def get_user_type(self, from_number):
        for user in self.config["USERS"]:
            if from_number in self.long_term_db.get_list_of(user+"_whatsapp_id"):
                return user
            
        for expert in self.config["EXPERTS"]:
            if from_number in self.long_term_db.get_list_of(expert+"_whatsapp_id"):
                return expert
            
        return None

    def onboard_response(self, data):
        from_number = data["from_number"]
        msg_id = data["msg_id"]
        msg_object = data["msg_object"]
        reply_id = data["reply_id"]
        lang = "en"
        for user in self.config["USERS"]:
            if from_number in self.long_term_db.get_list_of(user+"_whatsapp_id"):
                user_type = user
                lang = self.long_term_db.get_rows(from_number, user+"_whatsapp_id")[0][
                    user + "_language"
                ]
        for expert in self.config["EXPERTS"]:
            if from_number in self.long_term_db.get_list_of(expert+"_whatsapp_id"):
                user_type = expert
                lang = self.long_term_db.get_rows(from_number, expert+"_whatsapp_id")[0][
                    expert + "_language"
                ]


        if msg_object["button"]["payload"] in self.yes_responses:
            onboard_wa_helper(self.config, self.logger, from_number, user_type, lang)
        else:
            text_message = "Thank you for your response."
            text = self.azure_translate.translate_text(
                text_message, "en", lang, self.logger
            )
            self.messenger.send_message(from_number, text, reply_to_msg_id=None)
        self.logger.add_log(
            sender_id=from_number,
            receiver_id="bot",
            message_id=msg_id,
            action_type="onboard",
            details={"text": msg_object["button"]["text"], "reply_to": reply_id},
            timestamp=datetime.now(),
        )

        return

    def expert_reminder_response(self, data):
        from_number = data["from_number"]
        msg_id = data["msg_id"]
        msg_object = data["msg_object"]
        reply_id = data["reply_id"]
        self.messenger.send_message(from_number, "Thank you for your response.", None)
        self.logger.add_log(
            sender_id=from_number,
            receiver_id="bot",
            message_id=msg_id,
            action_type="expert reminder response",
            details={"text": msg_object["context"]["id"], "reply_to": reply_id},
            timestamp=datetime.now(),
        )
        return

    def check_expiration(self, from_number, user_type, row_lt):
        if row_lt.get("is_expired", False):
            message_text = "Your account has expired. Please contact your admin."
            source_lang = row_lt[user_type + "_language"]
            text = self.azure_translate.translate_text(
                message_text, "en", source_lang, self.logger
            )
            self.messenger.send_message(from_number, text, None)
            return True
        else:
            return False

    def handle_language_poll_response(self, data):
        print("Handling language poll response")
        from_number = data["from_number"]
        msg_id = data["msg_id"]
        user_id = data["user_id"]
        msg_object = data["msg_object"]
        user_type = data["user_type"]
        language_detected = data["lang_detected"]
        self.logger.add_log(
            sender_id=from_number,
            receiver_id="bot",
            message_id=msg_id,
            action_type="language_poll_response",
            details={
                "text": msg_object["interactive"]["list_reply"]["title"],
                "reply_to": msg_object["context"]["id"],
            },
            timestamp=datetime.now(),
        )
        
        row_lt = self.long_term_db.get_rows(user_id, "user_id")[0]

        for message in self.welcome_messages["users"][language_detected]:
            self.messenger.send_message(from_number, message)
        audio_file = (
            "onboarding/welcome_messages_users_"
            + language_detected
            + ".aac"
        )
        audio_file = os.path.join(os.environ['DATA_PATH'], audio_file)
        self.messenger.send_audio(audio_file, from_number)
        print("Sending language poll")
        self.messenger.send_language_poll(
            from_number,
            self.language_prompts[language_detected],
            self.language_prompts[language_detected + "_title"],
        )
        self.long_term_db.add_language(
            row_lt["_id"], language_detected, user_type + "_language"
        )
        return

    def answer_query_text(self, data):
        # data is a dictionary that contains from_number, msg_id, query
        print("Answering query text", data)
        from_number = data["from_number"]
        msg_id = data["msg_id"]
        user_id = data["user_id"]
        message = data["message"]
        translated_message = data["translated_message"]
        source_lang = data["source_lang"]
        user_type = data["user_type"]
        msg_type = data["msg_type"]

        db_id = self.user_conv_db.insert_row(
            user_id = user_id,
            user_type = user_type,
            message_id = msg_id,
            message_type = msg_type,
            message_source_lang = message,
            source_language = source_lang,
            message_translated = translated_message,
            audio_blob_path = None if msg_type != "audio" else data["blob_name"],
            message_timestamp = datetime.now()
        ).inserted_id

        gpt_output, citations, query_type = self.knowledge_base.answer_query(
            self.user_conv_db, db_id, self.logger
        )
        citations = "".join(citations)
        citations_str = citations

        print("GPT output: ", gpt_output)

        if msg_type == "text" or msg_type == "interactive":
            audio_msg_id = None
            gpt_output_source = self.azure_translate.translate_text(
                gpt_output, "en", source_lang, self.logger
            )
            sent_msg_id = self.messenger.send_message(
                from_number, gpt_output_source, msg_id
            )



        if msg_type == "audio":
            audio_input_file = "test_audio_input.aac"
            audio_output_file = "test_audio_output.aac"
            gpt_output_source = self.azure_translate.text_translate_speech(
                gpt_output,
                source_lang + "-IN",
                audio_output_file[:-3] + "wav",
                self.logger,
            )
            subprocess.run(
                [
                    "ffmpeg",
                    "-i",
                    audio_output_file[:-3] + "wav",
                    "-codec:a",
                    "aac",
                    audio_output_file,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            sent_msg_id = self.messenger.send_message(
                from_number, gpt_output_source, msg_id
            )
            audio_msg_id = self.messenger.send_audio(
                audio_output_file, from_number, msg_id
            )
            utils.remove_extra_voice_files(audio_input_file, audio_output_file)

        print("GPT output: ", gpt_output)

        self.user_conv_db.add_llm_response(
            message_id=msg_id,
            query_type=query_type,
            llm_response=gpt_output,
            citations=citations_str)

        self.bot_conv_db.insert_row(
            receiver_id=from_number,
            message_type="query_response",
            message_id=sent_msg_id,
            audio_message_id=audio_msg_id,
            message_source_lang=gpt_output_source,
            message_language=source_lang,
            message_english=gpt_output,
            message_timestamp=datetime.now(),
            transaction_message_id=msg_id,
        )


        if (
            self.config["SEND_POLL"]
            and query_type != "small-talk"
        ):
            self.messenger.send_reaction(from_number, sent_msg_id, "\u2753")
            if msg_type == "audio":
                self.messenger.send_reaction(from_number, audio_msg_id, "\u2753")
            self.messenger.send_correction_poll_expert(
                self.database, self.long_term_db, db_id
            )

        if self.config["SUGGEST_NEXT_QUESTIONS"]:
            print("Sending suggestions")
            self.send_suggestions(
                {
                    "from_number": from_number,
                    "db_id": db_id,
                    "user_id": user_id,
                    "query": translated_message,
                    "gpt_output": gpt_output,
                    "source_lang": source_lang,
                    "user_type": user_type,
                    "query_type": query_type,
                    "transaction_message_id": msg_id,
                }
            )

        return

    def send_suggestions(self, data):
        # data is a dictionary that contains from_number, msg_id, query
        from_number = data["from_number"]
        db_id = data["db_id"]
        user_id = data["user_id"]
        query = data["query"]
        gpt_output = data["gpt_output"]
        source_lang = data["source_lang"]
        user_type = data["user_type"]
        query_type = data["query_type"]

        if (
            (not gpt_output.strip().startswith("I do not know the answer to your question"))
            and query_type != "small-talk"
        ):
            next_questions = None
            
            next_questions = self.knowledge_base.follow_up_questions(
                query, gpt_output, user_type, self.logger
            )
            questions_source = []
            for question in next_questions:
                question_source = self.azure_translate.translate_text(
                    question, "en", source_lang, self.logger
                )
                questions_source.append(question_source)
            title, list_title = (
                self.onboarding_questions[source_lang]["title"],
                self.onboarding_questions[source_lang]["list_title"],
            )
            suggested_ques_msg_id = self.messenger.send_suggestions(
                from_number, title, list_title, questions_source
            )

            self.bot_conv_db.insert_row(
                receiver_id=from_number,
                message_type="suggested_questions",
                message_id=suggested_ques_msg_id,
                audio_message_id=None,
                message_source_lang=questions_source,
                message_language=source_lang,
                message_english=next_questions,
                message_timestamp=datetime.now(),
                transaction_message_id=data["transaction_message_id"],
            )


        elif False and self.database.get_next_questions(user_id, user_type):
            next_questions = self.database.get_next_questions(user_id, user_type)
            print("Next questions: ", next_questions)
            questions_source = []
            for question in next_questions:
                question_source = self.azure_translate.translate_text(
                    question, "en", source_lang, self.logger
                )
                questions_source.append(question_source)

            self.add_next_questions(db_id, next_questions)
            title, list_title = (
                self.onboarding_questions[source_lang]["title"],
                self.onboarding_questions[source_lang]["list_title"],
            )
            self.messenger.send_suggestions(
                from_number, title, list_title, questions_source
            )

    def handle_response_user(self, data):
        # data is a dictionary that contains from_number, msg_id, msg_object, user_type
        from_number = data["from_number"]
        msg_id = data["msg_id"]
        user_id = data["user_id"]
        reply_id = data.get("reply_id", None)
        msg_object = data["msg_object"]
        user_type = data["user_type"]
        msg_type = msg_object["type"]
        if (
            msg_object["type"] == "interactive"
            and msg_object["interactive"]["type"] == "list_reply"
            and msg_object["interactive"]["list_reply"]["id"][:5] == "LANG_"
        ):
            lang_detected = msg_object["interactive"]["list_reply"]["id"][5:-1].lower()
            self.handle_language_poll_response(
                {
                    "msg_object": msg_object,
                    "from_number": from_number,
                    "msg_id": msg_id,
                    "user_id": user_id,
                    "user_type": user_type,
                    "lang_detected": lang_detected,
                }
            )
            return

        if msg_object.get("text") or (
            msg_object["type"] == "interactive"
            and msg_object["interactive"]["type"] == "list_reply"
            and msg_object["interactive"]["list_reply"]["id"][:5] == "QUEST"
        ):
            source_language = self.long_term_db.get_rows(
                from_number, user_type + "_whatsapp_id"
            )[0][user_type + "_language"]

            if msg_type == "interactive":
                msg_body = msg_object["interactive"]["list_reply"]["description"]
                self.logger.add_log(
                    sender_id=from_number,
                    receiver_id="bot",
                    message_id=msg_id,
                    action_type="click_suggestion",
                    details={"suggestion_text": msg_body},
                    timestamp=datetime.now(),
                )
            elif msg_type == "text":
                msg_body = msg_object["text"]["body"]
                self.logger.add_log(
                    sender_id=from_number,
                    receiver_id="bot",
                    message_id=msg_id,
                    action_type="send_message",
                    details={"text": msg_body, "reply_to": None},
                    timestamp=datetime.now(),
                )
            translated_message = self.azure_translate.translate_text(
                msg_body,
                source_language=source_language,
                target_language="en",
                logger=self.logger,
            )
            response = self.answer_query_text(
                {
                    "from_number": from_number,
                    "msg_id": msg_id,
                    "user_id": user_id,
                    "message": msg_body,
                    "translated_message": translated_message,
                    "source_lang": source_language,
                    "user_type": user_type,
                    "msg_type": msg_type,
                }
            )
            return
        if msg_type == "audio":
            audio_input_file = "test_audio_input.ogg"
            audio_output_file = "test_audio_output.aac"
            utils.remove_extra_voice_files(audio_input_file, audio_output_file)
            self.messenger.download_audio(msg_object, audio_input_file)
            subprocess.call(
                ["ffmpeg", "-i", audio_input_file, audio_input_file[:-3] + "wav"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            connect_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING").strip()
            blob_service_client = BlobServiceClient.from_connection_string(connect_str)
            container_name = self.config["AZURE_BLOB_CONTAINER_NAME"].strip()

            blob_name = str(datetime.now()) + "_" + str(from_number) + ".aac"
            blob_client = blob_service_client.get_blob_client(
                container=container_name, blob=blob_name
            )
            with open(file=audio_input_file, mode="rb") as data:
                blob_client.upload_blob(data)

            source_language = self.long_term_db.get_rows(
                from_number, user_type + "_whatsapp_id"
            )[0][user_type + "_language"]
            source_lang_text, eng_text = self.azure_translate.speech_translate_text(
                audio_input_file[:-3] + "wav", source_language, self.logger, blob_name
            )
            self.logger.add_log(
                sender_id=from_number,
                receiver_id="bot",
                message_id=msg_id,
                action_type="send_message_audio",
                details={"message": source_lang_text, "reply_to": None},
                timestamp=datetime.now(),
            )
            response = self.answer_query_text(
                {
                    "from_number": from_number,
                    "msg_id": msg_id,
                    "user_id": user_id,
                    "message": source_lang_text,
                    "translated_message": eng_text,
                    "source_lang": source_language,
                    "user_type": user_type,
                    "msg_type": msg_type,
                    "blob_name": blob_name,
                }
            )
            return

    def handle_response_expert(self, data):
        msg_object = data["msg_object"]
        msg_type = msg_object["type"]

        if (
            msg_type == "interactive"
            and msg_object["interactive"]["type"] == "button_reply"
            and msg_object["interactive"]["button_reply"]["id"][:12] == "POLL_PRIMARY"
        ):
            self.messenger.receive_correction_poll_expert(
                self.database, self.long_term_db, msg_object, self.azure_translate
            )
        elif msg_type == "text":
            self.messenger.get_correction_from_expert(
                self.database,
                msg_object,
                self.azure_translate,
                self.long_term_db,
                self.knowledge_base,
            )
