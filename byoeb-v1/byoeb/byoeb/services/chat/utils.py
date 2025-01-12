import byoeb.services.chat.constants as constants
from typing import List
from byoeb.models.message_category import MessageCategory
from byoeb_core.models.byoeb.message_context import ByoebMessageContext
from byoeb.chat_app.configuration.config import bot_config

def has_audio_additional_info(
    byoeb_message: ByoebMessageContext
):
    return (
        byoeb_message.message_context.additional_info is not None and
        constants.DATA in byoeb_message.message_context.additional_info and
        constants.MIME_TYPE in byoeb_message.message_context.additional_info and
        "audio" in byoeb_message.message_context.additional_info.get(constants.MIME_TYPE)
    )

def has_interactive_list_additional_info(
    byoeb_message: ByoebMessageContext
):
    return (
        byoeb_message.message_context.additional_info is not None and
        constants.DESCRIPTION in byoeb_message.message_context.additional_info and
        constants.ROW_TEXTS in byoeb_message.message_context.additional_info
    )

def has_interactive_button_additional_info(
    byoeb_message: ByoebMessageContext
):
    return (
        byoeb_message.message_context.additional_info is not None and
        "button_titles" in byoeb_message.message_context.additional_info
    )

def has_template_additional_info(
    byoeb_message: ByoebMessageContext
):
    return (    
        byoeb_message.message_context.additional_info is not None and
        constants.TEMPLATE_NAME in byoeb_message.message_context.additional_info and
        constants.TEMPLATE_LANGUAGE in byoeb_message.message_context.additional_info and
        constants.TEMPLATE_PARAMETERS in byoeb_message.message_context.additional_info
    )

def has_text(
    byoeb_message: ByoebMessageContext
):
    return (
        byoeb_message.message_context.message_source_text is not None
    )

def get_last_active_duration_seconds(timestamp: str):
    from datetime import datetime
    
    # Convert Unix timestamp string to a datetime object
    last_active_time = datetime.fromtimestamp(int(timestamp))
    
    # Calculate the duration since last active
    return (datetime.now() - last_active_time).total_seconds()

def get_expert_byoeb_messages(byoeb_messages: List[ByoebMessageContext]):
    expert_user_types = bot_config["expert"]
    expert_messages = [
        byoeb_message for byoeb_message in byoeb_messages
        if byoeb_message.user is not None and byoeb_message.user.user_type in expert_user_types.values()
    ]
    return expert_messages

def get_user_byoeb_messages(byoeb_messages: List[ByoebMessageContext]):
    regular_user_type = bot_config["regular"]["user_type"]
    user_messages = [
        byoeb_message for byoeb_message in byoeb_messages 
        if byoeb_message.user is not None and byoeb_message.user.user_type == regular_user_type
    ]
    return user_messages

def get_read_receipt_byoeb_messages(byoeb_messages: List[ByoebMessageContext]):
    read_receipt_messages = [
        byoeb_message for byoeb_message in byoeb_messages
        if byoeb_message.message_category == MessageCategory.READ_RECEIPT.value
    ]
    return read_receipt_messages
    