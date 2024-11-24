import json
import byoeb_core.models.whatsapp.incoming as incoming_message
from byoeb_core.models.byoeb.message_context import (
    ByoebMessageConext,
    MessageContext,
    ReplyContext,
    MediaContext
)
from byoeb_core.models.byoeb.user import User

def convert_regular_message(original_message) -> ByoebMessageConext:
    byoeb_message_type = None
    message_text = None
    message_audio = None
    message_mime = None
    reply_to_message_id = None
    if isinstance(original_message, str):
        original_message = json.loads(original_message)
    regular_message = incoming_message.WhatsAppRegularMessageBody.model_validate(original_message)
    timestamp = regular_message.entry[0].changes[0].value.messages[0].timestamp
    from_number = regular_message.entry[0].changes[0].value.from_
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
    
    return ByoebMessageConext(
        channel_type="whatsapp",
        user=User(
            phone_number_id=from_number
        ),
        message_context=MessageContext(
            message_id=message_id,
            message_type=byoeb_message_type,
            message_source_text=message_text,
            media_c=MediaContext(
                media_id=message_audio,
                mime_type=message_mime
            )
        ),
        reply_context=ReplyContext(
            reply_to_message_id=reply_to_message_id
        ),
        incoming_timestamp=timestamp
    )

def convert_template_message(original_message) -> ByoebMessageConext:
    if isinstance(original_message, str):
        original_message = json.loads(original_message)
    template_message = incoming_message.WhatsAppTemplateMessageBody.model_validate(original_message)
    timestamp = template_message.entry[0].changes[0].value.messages[0].timestamp
    from_number = template_message.entry[0].changes[0].value.from_
    message_id = template_message.entry[0].changes[0].value.messages[0].id
    message_type = template_message.entry[0].changes[0].value.messages[0].type
    if message_type == "button":
        message_text = template_message.entry[0].changes[0].value.messages[0].button.text
        byoeb_message_type = "template_button"
    reply_to_message_id = template_message.entry[0].changes[0].value.messages[0].context.id
    byoeb_message_type = "template"

def convert_interactive_message(original_message) -> ByoebMessageConext:
    if isinstance(original_message, str):
        original_message = json.loads(original_message)
    interactive_message = incoming_message.WhatsAppInteractiveMessageBody.model_validate(original_message)
    timestamp = interactive_message.entry[0].changes[0].value.messages[0].timestamp
    from_number = interactive_message.entry[0].changes[0].value.from_
    message_id = interactive_message.entry[0].changes[0].value.messages[0].id
    message_type = interactive_message.entry[0].changes[0].value.messages[0].interactive.type
    if message_type == "button_reply":
        message_text = interactive_message.entry[0].changes[0].value.messages[0].interactive.button_reply.title
        byoeb_message_type = "interactive_button_reply"
    elif message_type == "list_reply":
        message_text = interactive_message.entry[0].changes[0].value.messages[0].interactive.list_reply.description
        byoeb_message_type = "interactive_list_reply"

def convert_whatsapp_to_byoeb_message(original_message, type):
    if type == "regular":
        return convert_regular_message(original_message)
    if type == "template":
        return convert_template_message(original_message)
    if type == "interactive":
        return convert_interactive_message(original_message)
    return False