import json
import byoeb_core.models.whatsapp.incoming as incoming_message

def validate_regular_message(original_message):
    if isinstance(original_message, str):
        original_message = json.loads(original_message)
    regular_message = incoming_message.WhatsAppRegularMessageBody.model_validate(original_message)
    try:
        if regular_message.entry[0].changes[0].value.messages[0].type == "text":
            return True
        if regular_message.entry[0].changes[0].value.messages[0].type == "audio":
            return True
    except:
        return False
    return False

def validate_template_message(original_message):
    if isinstance(original_message, str):
        original_message = json.loads(original_message)
    template_message = incoming_message.WhatsAppTemplateMessageBody.model_validate(original_message)
    try:
        if template_message.entry[0].changes[0].value.messages[0].type == "button":
            return True
    except:
        return False
    return False

def validate_interactive_message(original_message):
    if isinstance(original_message, str):
        original_message = json.loads(original_message)
    interactive_message = incoming_message.WhatsAppInteractiveMessageBody.model_validate(original_message)
    try:
        if interactive_message.entry[0].changes[0].value.messages[0].type == "interactive":
            return True
    except:
        return False
    return False

def validate_status_message(original_message):
    if isinstance(original_message, str):
        original_message = json.loads(original_message)
    status_message = incoming_message.WhatsAppStatusMessageBody
    try:
        if status_message.entry[0].changes[0].value.statuses is not None:
            return True
    except:
        return False
    return False

def validate_whatsapp_message(original_message):
    if validate_regular_message(original_message):
        return True, "regular"
    if validate_template_message(original_message):
        return True, "template"
    if validate_interactive_message(original_message):
        return True, "interactive"
    if validate_status_message(original_message):
        return True, "status"
    return False, None
