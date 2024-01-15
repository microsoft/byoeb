from abc import ABC, abstractmethod
import sys
import os

sys.path.append(os.path.dirname(__file__))
src_path = os.path.join(os.environ["APP_PATH"], "src")
print(src_path)

from conversation_database import (
    ConversationDatabase,
    LongTermDatabase,
    LoggingDatabase,
)


class BaseMessenger(ABC):
    @abstractmethod
    def __init__(self, config, logger: LoggingDatabase):
        pass

    @abstractmethod
    def send_message(
        self,
        to_number: str,
        msg_body: str,
        reply_to_msg_id: str = None,
    ):
        pass

    @abstractmethod
    def send_reaction(
        self,
        to_number: str,
        reply_to_msg_id: str = None,
        emoji: str = "👍",
    ):
        pass

    @abstractmethod
    def send_poll(
        self,
        to_number: str,
        poll_string: str,
        reply_to_msg_id: str = None,
        poll_id: str = None,
        send_to: str = None,
    ):
        pass

    @abstractmethod
    def send_correction_poll_expert(
        self,
        database: ConversationDatabase,
        long_term_db: LongTermDatabase,
        db_id: str,
        escalation: bool,
    ):
        pass


    @abstractmethod
    def send_language_poll(
        self,
        to_number: str,
        poll_string: str,
    ):
        pass

    @abstractmethod
    def send_suggestions(
        self,
        to_number: str,
        text_poll: str = None,
        questions: list = None,
    ):
        pass

    @abstractmethod
    def send_audio(
        self,
        audio_output_file: str,
        to_number: str,
        reply_to_msg_id: str = None,
    ):
        pass
