import byoeb.services.chat.constants as constants
from byoeb_core.models.byoeb.message_context import ByoebMessageContext

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