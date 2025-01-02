from enum import Enum

class MessageCategory(Enum):
    BOT_TO_USER = "bot_to_byoebuser"
    BOT_TO_USER_RESPONSE = "bot_to_byoebuser_response"
    BOT_TO_EXPERT = "bot_to_byoebexpert"
    BOT_TO_EXPERT_RESPONSE = "bot_to_byoebexpert_response"
    BOT_TO_EXPERT_VERIFICATION = "bot_to_byoebexpert_verification"
    USER_TO_BOT = "byoebuser_to_bot"
    EXPERT_TO_BOT = "byoebexpert_to_bot",
    READ_RECEIPT = "read_receipt"