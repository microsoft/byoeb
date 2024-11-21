import json
import byoeb_core.models.whatsapp.incoming as incoming_message

def convert_regular_message(original_message):
    if isinstance(original_message, str):
        original_message = json.loads(original_message)
    regular_message = incoming_message.WhatsAppRegularMessageBody.model_validate(original_message)

def convert_template_message(original_message):
    if isinstance(original_message, str):
        original_message = json.loads(original_message)
    template_message = incoming_message.WhatsAppTemplateMessageBody.model_validate(original_message)

def convert_interactive_message(original_message):
    if isinstance(original_message, str):
        original_message = json.loads(original_message)
    interactive_message = incoming_message.WhatsAppInteractiveMessageBody.model_validate(original_message)


def convert_whatsapp_to_byoeb_message(original_message, type):
    if type == "regular":
        return convert_regular_message(original_message)
    if type == "template":
        return convert_template_message(original_message)
    if type == "interactive":
        return convert_interactive_message(original_message)
    return False