import json
import uuid
import byoeb_core.models.whatsapp.incoming as incoming_message
from typing import List
from byoeb_core.models.byoeb.message_context import (
    ByoebMessageContext,
    MessageContext,
    ReplyContext,
    MediaContext
)
from byoeb_core.models.byoeb.message_status import ByoebMessageStatus
from byoeb_core.models.byoeb.user import User

def convert_regular_message(original_message) -> ByoebMessageContext:
    byoeb_message_type = None
    message_text = None
    message_audio = None
    message_mime = None
    reply_to_message_id = None
    if isinstance(original_message, str):
        original_message = json.loads(original_message)
    regular_message = incoming_message.WhatsAppRegularMessageBody.model_validate(original_message)
    timestamp = regular_message.entry[0].changes[0].value.messages[0].timestamp
    from_number = regular_message.entry[0].changes[0].value.messages[0].from_
    message_id = regular_message.entry[0].changes[0].value.messages[0].id
    message_type = regular_message.entry[0].changes[0].value.messages[0].type
    if message_type == "text":
        message_text = regular_message.entry[0].changes[0].value.messages[0].text.body
        byoeb_message_type = "regular_text"
    elif message_type == "audio":
        message_audio = regular_message.entry[0].changes[0].value.messages[0].audio.id
        message_mime = regular_message.entry[0].changes[0].value.messages[0].audio.mime_type
        byoeb_message_type = "regular_audio"
    
    if regular_message.entry[0].changes[0].value.messages[0].context is not None:
        reply_to_message_id = regular_message.entry[0].changes[0].value.messages[0].context.id
    
    message_info = None
    if message_audio is not None:
        message_info = MediaContext(
            media_id=message_audio,
            mime_type=message_mime
        )
    return ByoebMessageContext(
        channel_type="whatsapp",
        user=User(
            phone_number_id=from_number
        ),
        message_context=MessageContext(
            message_id=message_id,
            message_type=byoeb_message_type,
            message_source_text=message_text,
            media_info=message_info
        ),
        reply_context=ReplyContext(
            reply_id=reply_to_message_id
        ),
        incoming_timestamp=timestamp
    )

def convert_template_message(original_message) -> ByoebMessageContext:
    message_text = None
    if isinstance(original_message, str):
        original_message = json.loads(original_message)
    template_message = incoming_message.WhatsAppTemplateMessageBody.model_validate(original_message)
    timestamp = template_message.entry[0].changes[0].value.messages[0].timestamp
    from_number = template_message.entry[0].changes[0].value.messages[0].from_
    message_id = template_message.entry[0].changes[0].value.messages[0].id
    message_type = template_message.entry[0].changes[0].value.messages[0].type
    if message_type == "button":
        message_text = template_message.entry[0].changes[0].value.messages[0].button.text
        byoeb_message_type = "template_button"
    reply_to_message_id = template_message.entry[0].changes[0].value.messages[0].context.id
    byoeb_message_type = "template"
    return ByoebMessageContext(
        channel_type="whatsapp",
        user=User(
            phone_number_id=from_number
        ),
        message_context=MessageContext(
            message_id=message_id,
            message_type=byoeb_message_type,
            message_source_text=message_text
        ),
        reply_context=ReplyContext(
            reply_id=reply_to_message_id
        ),
        incoming_timestamp=timestamp
    )

def convert_interactive_message(original_message) -> ByoebMessageContext:
    message_text = None
    byoeb_message_type = None
    if isinstance(original_message, str):
        original_message = json.loads(original_message)
    interactive_message = incoming_message.WhatsAppInteractiveMessageBody.model_validate(original_message)
    timestamp = interactive_message.entry[0].changes[0].value.messages[0].timestamp
    from_number = interactive_message.entry[0].changes[0].value.messages[0].from_
    message_id = interactive_message.entry[0].changes[0].value.messages[0].id
    message_type = interactive_message.entry[0].changes[0].value.messages[0].interactive.type
    if message_type == "button_reply":
        message_text = interactive_message.entry[0].changes[0].value.messages[0].interactive.button_reply.title
        byoeb_message_type = "interactive_button_reply"
    elif message_type == "list_reply":
        message_text = interactive_message.entry[0].changes[0].value.messages[0].interactive.list_reply.description
        byoeb_message_type = "interactive_list_reply"
    reply_to_message_id = interactive_message.entry[0].changes[0].value.messages[0].context.id
    return ByoebMessageContext(
        channel_type="whatsapp",
        user=User(
            phone_number_id=from_number
        ),
        message_context=MessageContext(
            message_id=message_id,
            message_type=byoeb_message_type,
            message_source_text=message_text
        ),
        reply_context=ReplyContext(
            reply_id=reply_to_message_id
        ),
        incoming_timestamp=timestamp
    )

def convert_status_message(original_message) -> ByoebMessageStatus:
    if isinstance(original_message, str):
        original_message = json.loads(original_message)
    status_message = incoming_message.WhatsAppStatusMessageBody.model_validate(original_message)
    timestamp = status_message.entry[0].changes[0].value.statuses[0].timestamp
    phone_number_id = status_message.entry[0].changes[0].value.statuses[0].recipient_id
    message_id = status_message.entry[0].changes[0].value.statuses[0].id
    message_status = status_message.entry[0].changes[0].value.statuses[0].status
    return ByoebMessageStatus(
        channel_type="whatsapp",
        message_id=message_id,
        status=message_status,
        recipient_id=phone_number_id,
        incoming_timestamp=timestamp
    )

def convert_whatsapp_to_byoeb_message(original_message, type):
    if type == "regular":
        return convert_regular_message(original_message)
    if type == "template":
        return convert_template_message(original_message)
    if type == "interactive":
        return convert_interactive_message(original_message)
    if type == "status":
        return convert_status_message(original_message)
    return False