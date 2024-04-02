from typing import Any
from io import BytesIO

import os
from azure_language_tools import translator
import subprocess
from datetime import datetime
from azure.storage.blob import BlobServiceClient
import numpy as np
import json
from knowledge_base import KnowledgeBase
from conversation_database import (
    ConversationDatabase,
    LongTermDatabase,
    LoggingDatabase,
)
from database import UserDB, UserConvDB, BotConvDB, ExpertConvDB, UserRelationDB
from messenger.whatsapp import WhatsappMessenger
import utils
from utils import remove_extra_voice_files
from onboard import onboard_wa_helper
from responder.base import BaseResponder


class WhatsappResponder(BaseResponder):
    def __init__(self, config):
        self.config = config
        self.knowledge_base = KnowledgeBase(config)
        # self.database = ConversationDatabase(config)
        # self.long_term_db = LongTermDatabase(config)
        self.logger = LoggingDatabase(config)
        self.messenger = WhatsappMessenger(config, self.logger)
        self.azure_translate = translator()

        self.user_db = UserDB(config)
        self.user_relation_db = UserRelationDB(config)
        

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

        self.category_to_expert = {}

        for expert in self.config["EXPERTS"]:
            # self.experts_types.append(self.config["EXPERTS"])
            # self.categories.append(self.config["EXPERTS"][expert])
            self.category_to_expert[self.config["EXPERTS"][expert]] = expert

    def check_user_type(self, from_number):
        row = self.user_db.get_from_whatsapp_id(from_number)

        if row:
            return row["user_type"], row
            
        return None, None

    def update_kb(self):
        self.knowledge_base = KnowledgeBase(self.config)

    def response(self, body):
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

        print("Entering response function")
        
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
        if self.check_expiration(row_lt):
            return


        unsupported_types = ["image", "document", "video", "location", "contacts"]
        if msg_type in unsupported_types:
            self.handle_unsupported_msg_types(msg_object, row_lt)
            return

        if msg_object.get("context", False) and msg_object["context"].get("id", False):
            reply_id = msg_object["context"]["id"]
            logs = self.logger.get_log_from_message_id(reply_id)
            if len(logs) > 0: 
                msg_log = logs[0]
                if (
                    msg_log["details"]["text"] == "user_onboard"
                    or msg_log["details"]["text"] == "expert_onboard"
                ):
                    self.onboard_response(msg_object, row_lt)
                    return
                if msg_log["details"]["text"] == "expert_reminder":
                    self.expert_reminder_response(msg_object, row_lt)
                    return



        if user_type in self.config["USERS"]:
            self.handle_response_user(msg_object, row_lt)
        elif user_type in self.config["EXPERTS"]:
            self.handle_response_expert(msg_object, row_lt)

        return

    def handle_unsupported_msg_types(self, msg_object, row_lt):
        # data is a dictionary that contains from_number, msg_id, msg_object
        print("Handling unsupported message types")
        msg_id = msg_object["id"]
        self.logger.add_log(
            sender_id=row_lt['whatsapp_id'],
            receiver_id="bot",
            message_id=msg_id,
            action_type="unsupported message format",
            details={"text": msg_object["type"], "reply_to": None},
            timestamp=datetime.now(),
        )
        text = "Sorry, this format is not supported right now, please send your queries as text/voice messages."
        
        translated_text = self.azure_translate.translate_text(
            text, "en", row_lt['user_language'], self.logger
        )
        self.messenger.send_message(
            row_lt['whatsapp_id'], translated_text, reply_to_msg_id=msg_id
        )
        return
    
    def onboard_response(self, msg_object, row_lt):
        user_type = row_lt["user_type"]
        msg_id = msg_object["id"]
        reply_id = msg_object["context"]["id"]

        if msg_object["button"]["payload"] in self.yes_responses:
            onboard_wa_helper(self.config, self.logger, row_lt['whatsapp_id'], user_type, row_lt['user_language'])
        else:
            text_message = "Thank you for your response."
            text = self.azure_translate.translate_text(
                text_message, "en", row_lt['user_language'], self.logger
            )
            self.messenger.send_message(row_lt['whatsapp_id'], text, reply_to_msg_id=None)
        self.logger.add_log(
            sender_id=row_lt['whatsapp_id'],
            receiver_id="bot",
            message_id=msg_id,
            action_type="onboard",
            details={"text": msg_object["button"]["text"], "reply_to": reply_id},
            timestamp=datetime.now(),
        )

        return

    def expert_reminder_response(self, msg_object, row_lt):
        msg_id = msg_object["id"]
        reply_id = msg_object["context"]["id"]
        self.messenger.send_message(row_lt['whatsapp_id'], "Thank you for your response.", None)
        self.logger.add_log(
            sender_id=row_lt['whatsapp_id'],
            receiver_id="bot",
            message_id=msg_id,
            action_type="expert reminder response",
            details={"text": msg_object["context"]["id"], "reply_to": reply_id},
            timestamp=datetime.now(),
        )
        return

    def check_expiration(self, row_lt):
        if row_lt.get("is_expired", False):
            message_text = "Your account has expired. Please contact your admin."
            source_lang = row_lt["user_language"]
            text = self.azure_translate.translate_text(
                message_text, "en", source_lang, self.logger
            )
            self.messenger.send_message(row_lt['whatsapp_id'], text, None)
            return True
        else:
            return False

    def handle_language_poll_response(self, msg_object, row_lt):
        print("Handling language poll response")
        msg_id = msg_object["id"]
        lang_detected = msg_object["interactive"]["list_reply"]["id"][5:-1].lower()
            

        self.logger.add_log(
            sender_id=row_lt['whatsapp_id'],
            receiver_id="bot",
            message_id=msg_id,
            action_type="language_poll_response",
            details={
                "text": msg_object["interactive"]["list_reply"]["title"],
                "reply_to": msg_object["context"]["id"],
            },
            timestamp=datetime.now(),
        )
        
        for message in self.welcome_messages["users"][lang_detected]:
            self.messenger.send_message(row_lt['whatsapp_id'], message)
        audio_file = (
            "onboarding/welcome_messages_users_"
            + lang_detected
            + ".aac"
        )
        audio_file = os.path.join(os.environ['DATA_PATH'], audio_file)
        self.messenger.send_audio(audio_file, row_lt['whatsapp_id'])
        print("Sending language poll")
        self.messenger.send_language_poll(
            row_lt['whatsapp_id'],
            self.language_prompts[lang_detected],
            self.language_prompts[lang_detected + "_title"],
        )

        self.user_db.update_user_language(row_lt['user_id'], lang_detected)
        return

    def answer_query_text(self, msg_id, message, translated_message, msg_type, row_lt, blob_name=None):
        print("Answering query")
        db_id = self.user_conv_db.insert_row(
            user_id = row_lt['user_id'],
            message_id = msg_id,
            message_type = msg_type,
            message_source_lang = message,
            source_language = row_lt['user_language'],
            message_translated = translated_message,
            audio_blob_path = None if msg_type != "audio" else blob_name,
            message_timestamp = datetime.now()
        ).inserted_id

        gpt_output, citations, query_type = self.knowledge_base.answer_query(
            self.user_conv_db, msg_id, self.logger
        )
        citations = "".join(citations)
        citations_str = citations

        print("GPT output: ", gpt_output)

        if msg_type == "text" or msg_type == "interactive":
            audio_msg_id = None
            gpt_output_source = self.azure_translate.translate_text(
                gpt_output, "en", row_lt['user_language'], self.logger
            )
            sent_msg_id = self.messenger.send_message(
                row_lt['whatsapp_id'], gpt_output_source, msg_id
            )



        if msg_type == "audio":
            audio_input_file = "test_audio_input.aac"
            audio_output_file = "test_audio_output.aac"
            gpt_output_source = self.azure_translate.text_translate_speech(
                gpt_output,
                row_lt['user_language'] + "-IN",
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
                row_lt['whatsapp_id'], gpt_output_source, msg_id
            )
            audio_msg_id = self.messenger.send_audio(
                audio_output_file, row_lt['whatsapp_id'], msg_id
            )
            utils.remove_extra_voice_files(audio_input_file, audio_output_file)

        print("GPT output: ", gpt_output)

        self.user_conv_db.add_query_type(
            message_id=msg_id,
            query_type=query_type
        )

        self.bot_conv_db.insert_row(
            receiver_id=row_lt['user_id'],
            message_type="query_response",
            message_id=sent_msg_id,
            audio_message_id=audio_msg_id,
            message_source_lang=gpt_output_source,
            message_language=row_lt['user_language'],
            message_english=gpt_output,
            reply_id=msg_id,
            citations=citations_str,
            message_timestamp=datetime.now(),
            transaction_message_id=msg_id,
        )



        row_query = self.user_conv_db.get_from_db_id(db_id)
            
        if (
            self.config["SEND_POLL"]
            and query_type != "small-talk"
        ):
            self.messenger.send_reaction(row_lt['whatsapp_id'], sent_msg_id, "\u2753")
            if msg_type == "audio":
                self.messenger.send_reaction(row_lt['whatsapp_id'], audio_msg_id, "\u2753")
            self.send_correction_poll_expert(row_lt, row_query)
        
        
        if self.config["SUGGEST_NEXT_QUESTIONS"]:
            print("Sending suggestions")
            self.send_suggestions(row_lt, row_query, gpt_output)

        

        return

    def send_suggestions(self, row_lt, row_query, gpt_output):


        source_lang = row_lt["user_language"]
        query = row_query["message_source_lang"]
        query_type = row_query["query_type"]

        if (
            (not gpt_output.strip().startswith("I do not know the answer to your question"))
            and query_type != "small-talk"
        ):
            next_questions = None
            
            next_questions = self.knowledge_base.follow_up_questions(
                query, gpt_output, row_lt['user_type'], self.logger
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
                row_lt['whatsapp_id'], title, list_title, questions_source
            )

        else:
            prev_row = self.bot_conv_db.find_with_receiver_id(row_query["user_id"], "suggested_questions")
            if prev_row is None:
                return
            next_questions = list(prev_row["message_english"])
            print("Next questions: ", next_questions)
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
                row_lt['whatsapp_id'], title, list_title, questions_source
            )

        self.bot_conv_db.insert_row(
            receiver_id=row_lt['user_id'],
            message_type="suggested_questions",
            message_id=suggested_ques_msg_id,
            audio_message_id=None,
            message_source_lang=questions_source,
            message_language=source_lang,
            message_english=next_questions,
            reply_id=None,
            citations=None,
            message_timestamp=datetime.now(),
            transaction_message_id=row_query['message_id'],
        )


    def handle_response_user(self, msg_object, row_lt):
        # data is a dictionary that contains from_number, msg_id, msg_object, user_type
        print("Handling user response")
        msg_type = msg_object["type"]
        user_id = row_lt['user_id'] 
        msg_id = msg_object["id"]
        if (
            msg_object["type"] == "interactive"
            and msg_object["interactive"]["type"] == "list_reply"
            and msg_object["interactive"]["list_reply"]["id"][:5] == "LANG_"
        ):
            self.handle_language_poll_response(msg_object, row_lt)
            return

        if msg_object.get("text") or (
            msg_object["type"] == "interactive"
            and msg_object["interactive"]["type"] == "list_reply"
            and msg_object["interactive"]["list_reply"]["id"][:5] == "QUEST"
        ):
            

            if msg_type == "interactive":
                msg_body = msg_object["interactive"]["list_reply"]["description"]
                self.logger.add_log(
                    sender_id=row_lt['whatsapp_id'],
                    receiver_id="bot",
                    message_id=msg_id,
                    action_type="click_suggestion",
                    details={"suggestion_text": msg_body},
                    timestamp=datetime.now(),
                )
            elif msg_type == "text":
                msg_body = msg_object["text"]["body"]
                self.logger.add_log(
                    sender_id=row_lt['whatsapp_id'],
                    receiver_id="bot",
                    message_id=msg_id,
                    action_type="send_message",
                    details={"text": msg_body, "reply_to": None},
                    timestamp=datetime.now(),
                )
            translated_message = self.azure_translate.translate_text(
                msg_body,
                source_language=row_lt['user_language'],
                target_language="en",
                logger=self.logger,
            )
            response = self.answer_query_text(msg_id, msg_body, translated_message, msg_type, row_lt)
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

            blob_name = str(datetime.now()) + "_" + str(row_lt['whatsapp_id']) + ".ogg"
            blob_client = blob_service_client.get_blob_client(
                container=container_name, blob=blob_name
            )
            with open(file=audio_input_file, mode="rb") as data:
                blob_client.upload_blob(data)

            
            source_lang_text, eng_text = self.azure_translate.speech_translate_text(
                audio_input_file[:-3] + "wav", row_lt['user_language'], self.logger, blob_name
            )
            self.logger.add_log(
                sender_id=row_lt['whatsapp_id'],
                receiver_id="bot",
                message_id=msg_id,
                action_type="send_message_audio",
                details={"message": source_lang_text, "reply_to": None},
                timestamp=datetime.now(),
            )
            response = self.answer_query_text(msg_id, source_lang_text, eng_text, msg_type, row_lt, blob_name)
            return


    def handle_response_expert(self, msg_object, row_lt):
        msg_type = msg_object["type"]

        if (
            msg_type == "interactive"
            and msg_object["interactive"]["type"] == "button_reply"
            and msg_object["interactive"]["button_reply"]["id"][:12] == "POLL_PRIMARY"
        ):
            self.receive_correction_poll_expert(msg_object, row_lt)
        elif msg_type == "text":
            self.get_correction_from_expert(msg_object, row_lt)


    def send_correction_poll_expert(self, row_lt, row_query, escalation=False):

        query_type = row_query["query_type"]
        expert_type = self.category_to_expert[query_type]
        user_secondary_id = self.user_relation_db.find_user_relations(row_lt['user_id'], expert_type)['user_id_secondary']
        expert_row_lt = self.user_db.get_from_user_id(user_secondary_id)
        
        row_bot_conv = self.bot_conv_db.find_with_transaction_id(row_query["message_id"], "query_response")


        user_type = row_lt["user_type"]
        
        poll_string = f"Was the bot's answer correct and complete?"

        citations = row_bot_conv["citations"]
        try:
            split_citations = citations.split("\n")
            split_citations = np.unique(
                np.array(
                    [
                        citation.replace("_", " ").replace("  ", " ").strip()
                        for citation in split_citations
                    ]
                )
            )
            final_citations = ", ".join([citation for citation in split_citations])
        except:
            final_citations = "No citations found."

        expert = self.category_to_expert[row_query['query_type']]
        if escalation is False:
            receiver = expert_row_lt["whatsapp_id"]
            forward_to = expert
        else:
            receiver = self.config["ESCALATION"][expert]['whatsapp_id']
            forward_to = expert


        

        poll_text = f'*Query*: "{row_query["message_english"]}" \n*Bot\'s Response*: {row_bot_conv["message_english"].strip()} \n\n*User*: {user_type} \n*Citations*: {final_citations.strip()}. \n\n{poll_string}'
        message_id = self.messenger.send_poll(
            receiver, poll_text, poll_id="POLL_PRIMARY", send_to=forward_to
        )

    

        
        self.bot_conv_db.insert_row(
            receiver_id=expert_row_lt["user_id"],
            message_type=f"poll_{'escalated' if escalation else 'primary'}",
            message_id=message_id,
            audio_message_id=None,
            message_source_lang=poll_text,
            message_language=expert_row_lt["user_language"],
            message_english=poll_text,
            reply_id=None,
            citations=None,
            message_timestamp=datetime.now(),
            transaction_message_id=row_query["message_id"],
        )

        if escalation:
            primary_poll = self.bot_conv_db.find_with_transaction_id(row_query["message_id"], "poll_primary")

            receiver_name = self.config["ESCALATION"][expert]['name']
            primanry_notif = expert_row_lt["whatsapp_id"]
            self.send_message(
                primanry_notif,
                "Escalating it to " + receiver_name,
                reply_to_msg_id=primary_poll["message_id"],
            )


        return message_id


    def receive_correction_poll_expert(self, msg_object, expert_row_lt):
        answer = msg_object["interactive"]["button_reply"]["title"]
        context_id = msg_object["context"]["id"]

        self.logger.add_log(
            sender_id=msg_object["from"],
            receiver_id="bot",
            message_id=msg_object["id"],
            action_type="receive_poll",
            details={"answer": answer, "reply_to": context_id},
            timestamp=datetime.now(),
        )

        poll = self.bot_conv_db.get_from_message_id(context_id)
        
        print(poll)



        if poll is None:
            self.messenger.send_message(
                msg_object["from"],
                f"Please reply to the query that you are trying to answer.",
                msg_object["id"],
            )
            return
        
        transaction_message_id = poll["transaction_message_id"]
        row_query = self.user_conv_db.get_from_message_id(transaction_message_id)

        
        if expert_row_lt['user_type'] != self.category_to_expert[row_query['query_type']]:
            self.messenger.send_message(
                expert_row_lt['whatsapp_id'],
                f"This query has been forwarded to the {self.category_to_expert[row_query['query_type']]}.",
                context_id,
            )
            return

        if row_query.get("resolved", False):
            self.messenger.send_message(
                expert_row_lt['whatsapp_id'],
                "This query has already been answered.",
                context_id,
            )
            return

        row_response = self.bot_conv_db.find_with_transaction_id(transaction_message_id, "query_response")
        user_row_lt = self.user_db.get_from_user_id(row_query["user_id"])
        
        print(row_query)
        print(user_row_lt)

        poll_responses = self.expert_conv_db.get_from_transaction_message_id(transaction_message_id, "poll_response")
        print(poll_responses)
        if len(poll_responses) > 0:
            poll_responses = sorted(poll_responses, key=lambda x: x['message_timestamp'])
            last_poll_response = poll_responses[-1]
            if last_poll_response['message'] == "No": # and last_poll_response["user_id"] != expert_row_lt["user_id"]:
                if last_poll_response["user_id"] == expert_row_lt["user_id"]:
                    self.messenger.send_message(
                        expert_row_lt['whatsapp_id'],
                        "You have already replied to this poll, please share the correction.",
                        context_id,
                    )
                else:
                    self.messenger.send_message(
                        expert_row_lt['whatsapp_id'],
                        "This query has already been answered.",
                        context_id,
                    )
                return

        
        # rows = self.expert_conv_db.get_from_transaction_message_id(transaction_message_id)
        # if len(rows) > 0:
        #     print(rows)
        #     return

        if answer == "Yes":
            self.messenger.send_message(
                expert_row_lt['whatsapp_id'],
                "Noted, thank you for the response.",
                context_id,
            )
            
            


            #Send green tick to the user messages
            self.messenger.send_reaction(
                user_row_lt['whatsapp_id'], row_response["message_id"], "\u2705"
            )
            if row_response["audio_message_id"]:
                self.messenger.send_reaction(
                    user_row_lt['whatsapp_id'], row_response["audio_message_id"], "\u2705"
                )
            text = f"This response has been verified by the {expert_row_lt['user_type']}."
            text_translated = self.azure_translate.translate_text(
                text, "en", user_row_lt["user_language"], self.logger
            )
            self.messenger.send_message(
                user_row_lt["whatsapp_id"],
                text_translated,
                row_query["message_id"],
            )

            #Send green tick to the responding expert    
            self.messenger.send_reaction(
                expert_row_lt['whatsapp_id'], poll["message_id"], "\u2705"
            )

            #Send green tick to other expert (if any)
            if poll['message_type'] == "poll_primary":
                poll_notif = self.bot_conv_db.find_with_transaction_id(transaction_message_id, "poll_escalated")
            else:
                poll_notif = self.bot_conv_db.find_with_transaction_id(transaction_message_id, "poll_primary")

            if poll_notif is not None:
                notif_row_lt = self.user_db.get_from_user_id(poll_notif["receiver_id"])
                self.messenger.send_reaction(
                    notif_row_lt['whatsapp_id'], poll_notif["message_id"], "\u2705"
                )

            self.user_conv_db.mark_resolved(transaction_message_id)
            self.expert_conv_db.insert_row(
                user_id=expert_row_lt["user_id"],
                message_type="poll_response",
                message_id=msg_object["id"],
                reply_id=context_id,
                message="Yes",
                message_timestamp=datetime.now(),
                transaction_message_id=transaction_message_id,
            )

        elif answer == "No":
            self.messenger.send_reaction(
                user_row_lt['whatsapp_id'], row_response["message_id"], "\u274C"
            )
            if row_response["audio_message_id"]:
                self.messenger.send_reaction(
                    user_row_lt['whatsapp_id'], row_response["audio_message_id"], "\u274C"
                )
            text = f"This answer is invalid. Please wait for the correct response from the {expert_row_lt['user_type']}."
            text_translated = self.azure_translate.translate_text(
                text, "en", user_row_lt["user_language"], self.logger
            )
            self.messenger.send_message(
                user_row_lt['whatsapp_id'],
                text_translated,
                row_response["message_id"],
            )
            self.messenger.send_message(
                expert_row_lt['whatsapp_id'],
                "Please reply with a correction to the query that you are trying to fix.",
                context_id,
            )
            self.expert_conv_db.insert_row(
                user_id=expert_row_lt["user_id"],
                message_type="poll_response",
                message_id=msg_object["id"],
                reply_id=context_id,
                message="No",
                message_timestamp=datetime.now(),
                transaction_message_id=transaction_message_id,
            )


        return
        
    
    def get_correction_from_expert(self, msg_object, expert_row_lt):
        
        if msg_object.get("context", False) == False:
            self.messenger.send_message(
                expert_row_lt['whatsapp_id'],
                "Please reply to the query you want to fix.",
                msg_object["id"],
            )
            return


        msg_body = msg_object["text"]["body"]
        context_id = msg_object["context"]["id"]

        self.logger.add_log(
            sender_id=msg_object["from"],
            receiver_id="bot",
            message_id=msg_object["id"],
            action_type="received_correction",
            details={"text": msg_body, "reply_to": context_id},
            timestamp=datetime.now(),
        )

        poll = self.bot_conv_db.get_from_message_id(context_id)

        if poll['message_type'] == 'consensus_poll':
            self.expert_conv_db.insert_row(
                user_id=expert_row_lt["user_id"],
                message_id=msg_object["id"],
                message_type="consensus_response",
                message=msg_body,
                reply_id=context_id,
                message_timestamp=datetime.now(),
                transaction_message_id=poll["transaction_message_id"],
            )
            self.messenger.send_message(
                msg_object["from"], "Thank you for the response.", msg_object["id"]
            )
            return
            

        if poll is None or (poll["message_type"] != "poll_primary" and poll["message_type"] != "poll_escalated"):
            self.messenger.send_message(
                msg_object["from"],
                f"Please reply to the query you want to fix.",
                msg_object["id"],
            )
            return
        
        transaction_message_id = poll["transaction_message_id"]

        row_query = self.user_conv_db.get_from_message_id(transaction_message_id)
        user_row_lt = self.user_db.get_from_user_id(row_query["user_id"])

        if row_query.get("resolved", False):
            self.messenger.send_message(
                expert_row_lt['whatsapp_id'],
                "This query has already been answered.",
                context_id,
            )
            return
        
        if expert_row_lt['user_type'] != self.category_to_expert[row_query['query_type']]:
            self.messenger.send_message(
                expert_row_lt['whatsapp_id'],
                f"This query has been forwarded to the {self.category_to_expert[row_query['query_type']]}.",
                context_id,
            )
            return
        
        row_response = self.bot_conv_db.find_with_transaction_id(transaction_message_id, "query_response")

        poll_responses = self.expert_conv_db.get_from_transaction_message_id(transaction_message_id, "poll_response")
        print(poll_responses)
        if len(poll_responses) == 0:
            self.messenger.send_message(
                expert_row_lt['whatsapp_id'],
                "Please reply to the poll of the query you are trying to fix before sending a correction.",
                context_id,
            )
            return
        else:
            poll_responses = sorted(poll_responses, key=lambda x: x['message_timestamp'])
            last_poll_response = poll_responses[-1]
            if last_poll_response['message'] != "No" and last_poll_response["user_id"] != expert_row_lt["user_id"]:
                self.messenger.send_message(
                    expert_row_lt['whatsapp_id'],
                    "This query has already been answered.",
                    context_id,
                )
                return

        db_id = self.expert_conv_db.insert_row(
            user_id=expert_row_lt["user_id"],
            message_id=msg_object["id"],
            message_type="correction",
            message=msg_body,
            reply_id=context_id,
            message_timestamp=datetime.now(),
            transaction_message_id=transaction_message_id,
        ).inserted_id

        row_correction = self.expert_conv_db.get_from_message_id(msg_object["id"])

            

        gpt_output = self.knowledge_base.generate_correction(row_query, row_response, row_correction, self.logger)
        gpt_output = gpt_output.strip('"')

        

        
        if row_query["message_type"] == "audio":
            corrected_audio_loc = "corrected_audio.wav"
            remove_extra_voice_files(
                corrected_audio_loc, corrected_audio_loc[:-3] + ".aac"
            )
            gpt_output_source = self.azure_translate.text_translate_speech(
                gpt_output, user_row_lt['user_language'] + "-IN", corrected_audio_loc, self.logger
            )

            updated_msg_id = self.messenger.send_message(
                user_row_lt['whatsapp_id'],
                gpt_output_source,
                row_query["message_id"],
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
            updated_audio_msg_id = self.messenger.send_audio(
                corrected_audio_loc[:-3] + ".aac",
                user_row_lt['whatsapp_id'],
                row_query["message_id"]
            )
            remove_extra_voice_files(
                corrected_audio_loc, corrected_audio_loc[:-3] + ".aac"
            )

            self.messenger.send_reaction(user_row_lt['whatsapp_id'], updated_msg_id, "\u2705")
            self.messenger.send_reaction(
                user_row_lt['whatsapp_id'], updated_audio_msg_id, "\u2705"
            )
        else:
            gpt_output_source = self.azure_translate.translate_text(
                gpt_output, "en", user_row_lt['user_language'], self.logger
            )
            updated_msg_id = self.messenger.send_message(
                user_row_lt['whatsapp_id'],
                gpt_output_source,
                row_query["message_id"],
            )
            updated_audio_msg_id = None
            self.messenger.send_reaction(user_row_lt['whatsapp_id'], updated_msg_id, "\u2705")

        self.bot_conv_db.insert_row(
            receiver_id=user_row_lt['user_id'],
            message_type="query_correction",
            message_id=updated_msg_id,
            audio_message_id=updated_audio_msg_id,
            message_source_lang=gpt_output_source,
            message_language=user_row_lt['user_language'],
            message_english=gpt_output,
            reply_id=row_query["message_id"],
            citations="expert_correction",
            message_timestamp=datetime.now(),
            transaction_message_id=transaction_message_id
        )

        expert = self.category_to_expert[row_query['query_type']]
        text = f"This response has been verified by the {expert}."
        msg_text = self.azure_translate.translate_text(text, "en", user_row_lt['user_language'], self.logger)
        self.messenger.send_message(user_row_lt["whatsapp_id"], msg_text, updated_msg_id)

        self.messenger.send_message(
            msg_object["from"], "Correction noted. Thank you.", msg_object["id"]
        )
        self.user_conv_db.mark_resolved(transaction_message_id)
        
        
        if row_query['message_type'] == 'audio':
            remove_extra_voice_files(
                corrected_audio_loc, corrected_audio_loc[:-3] + ".aac"
            )
        return
    

    def send_query_expert(self, expert_row_lt, query_row):

        query = query_row["message_source_lang"]

        message = f"*Query*: {query}"

        message_id = self.messenger.send_message(
            expert_row_lt['whatsapp_id'], message, None
        )

        if query_row["message_type"] == "audio":
            audio_file = query_row["audio_blob_path"]
            
            
            connect_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING").strip()
            blob_service_client = BlobServiceClient.from_connection_string(connect_str)
            container_name = self.config["AZURE_BLOB_CONTAINER_NAME"].strip()

            blob_client = blob_service_client.get_blob_client(container=container_name, blob=audio_file)
            download_file_path = "original_audio.ogg"
            with open(download_file_path, "wb") as download_file:
                download_file.write(blob_client.download_blob().readall())
            
            audio_msg_id = self.messenger.send_audio(audio_file, expert_row_lt['whatsapp_id'], message_id)

        else:
            audio_msg_id = None

        self.bot_conv_db.insert_row(
            receiver_id=expert_row_lt["user_id"],
            message_type="consensus_poll", #ask Mohit
            message_id=message_id,
            audio_message_id=audio_msg_id,
            message_source_lang=query,
            message_language=query_row["source_language"],
            message_english=query,
            reply_id=None,
            citations=None,
            message_timestamp=datetime.now(),
            transaction_message_id=query_row["message_id"],
        )