import uuid
import byoeb_core.models.whatsapp.requests as wa_requests
import byoeb_core.convertor.audio_convertor as audio_convertor
from byoeb_core.models.byoeb.message_context import ByoebMessageContext
from byoeb_core.models.whatsapp.message_context import WhatsappMessageReplyContext
from byoeb_integrations.channel.whatsapp.meta.async_whatsapp_client import WhatsAppMessageTypes

def get_whatsapp_text_request_from_byoeb_message(
    byoeb_message: ByoebMessageContext
):
    message_text = byoeb_message.message_context.message_source_text
    phone_number_id = byoeb_message.user.phone_number_id
    messaging_product = "whatsapp"
    context = None
    if byoeb_message.reply_context is not None:
        reply_id = byoeb_message.reply_context.reply_id
        context = WhatsappMessageReplyContext(
            message_id=reply_id
        )
    text_message = wa_requests.WhatsAppMessage(
            messaging_product=messaging_product,
            to=phone_number_id,
            type=WhatsAppMessageTypes.TEXT.value,
            text=wa_requests.Text(body=message_text),
            context=context
        )
    return text_message.model_dump()

def get_whatsapp_audio_request_from_byoeb_message(
    byoeb_message: ByoebMessageContext
):
    audio_data = byoeb_message.message_context.additional_info["data"]
    phone_number_id = byoeb_message.user.phone_number_id
    messaging_product = "whatsapp"
    context = None
    if byoeb_message.reply_context is not None:
        reply_id = byoeb_message.reply_context.reply_id
        context = WhatsappMessageReplyContext(
            message_id=reply_id
        )
    audio_ogg = audio_convertor.wav_to_ogg_opus_bytes(audio_data)
    audio_message = wa_requests.WhatsAppMediaMessage(
        messaging_product=messaging_product,
        to=phone_number_id,
        type=WhatsAppMessageTypes.AUDIO.value,
        media=wa_requests.MediaData(
            data=audio_ogg,
            mime_type="audio/ogg"
        ),
        context=context
    )
    return audio_message.model_dump()

def get_whatsapp_interactive_button_request_from_byoeb_message(
    byoeb_message: ByoebMessageContext
):
    def get_button(title):
        poll_id = str(uuid.uuid4())
        return wa_requests.InteractiveActionButton(
            reply=wa_requests.InteractiveReply(
                id=poll_id,
                title=title
            )
        )
    button_titles = byoeb_message.message_context.additional_info["button_titles"]
    buttons = [get_button(title) for title in button_titles]
    message_text = byoeb_message.message_context.message_source_text
    phone_number_id = byoeb_message.user.phone_number_id
    interactive_message = wa_requests.WhatsAppInteractiveMessage(
        messaging_product="whatsapp",
        to=phone_number_id,
        type=WhatsAppMessageTypes.INTERACTIVE.value,
        interactive=wa_requests.Interactive(
            body=wa_requests.InteractiveBody(
                text=message_text
            ),
            action=wa_requests.InteractiveAction(
                buttons=buttons
            )
        )
    )
    return interactive_message.model_dump()

def get_whatsapp_interactive_list_request_from_byoeb_message(
    byoeb_message: ByoebMessageContext
):
    def get_section_row(description):
        return wa_requests.InteractiveSectionRow(
            id=str(uuid.uuid4()),
            title=" ",
            description=description
        )
    def get_section(row_texts):
        rows = [get_section_row(row_text) for row_text in row_texts]
        return wa_requests.InteractiveActionSection(
            title="Default Section",
            rows=rows
        )
    description = byoeb_message.message_context.additional_info["description"]
    row_texts = byoeb_message.message_context.additional_info["row_texts"]
    message_text = byoeb_message.message_context.message_source_text
    phone_number_id = byoeb_message.user.phone_number_id
    context = None
    if byoeb_message.reply_context is not None:
        reply_id = byoeb_message.reply_context.reply_id
        context = WhatsappMessageReplyContext(
            message_id=reply_id
        )
    interactive_message = wa_requests.WhatsAppInteractiveMessage(
        messaging_product="whatsapp",
        to=phone_number_id,
        type=WhatsAppMessageTypes.INTERACTIVE.value,
        interactive=wa_requests.Interactive(
            type=wa_requests.InteractiveMessageTypes.LIST.value,
            body=wa_requests.InteractiveBody(
                text=message_text
            ),
            action=wa_requests.InteractiveAction(
                button=description,
                sections=[
                    get_section(row_texts),
                ]
            )
        ),
        context=context
    )
    return interactive_message.model_dump()

def get_whatsapp_template_request_from_byoeb_message(
    byoeb_message: ByoebMessageContext
):
    template_parameters = byoeb_message.message_context.additional_info["template_parameters"]
    template_name = byoeb_message.message_context.additional_info["template_name"]
    template_language = byoeb_message.message_context.additional_info["template_language"]
    phone_number_id = byoeb_message.user.phone_number_id
    parameters = [
        wa_requests.TemplateParameter(
            type="text",
            text=parameter
        ) for parameter in template_parameters
    ]
    component = wa_requests.TemplateComponent(
        type="body",
        parameters=parameters
    )
    template = wa_requests.Template(
        name =template_name,
        language=wa_requests.TemplateLanguage(
            code=template_language,
        ),
        components=[component]
    )
    template_message = wa_requests.WhatsAppTemplateMessage(
        messaging_product="whatsapp",
        to=phone_number_id,
        type=WhatsAppMessageTypes.TEMPLATE.value,
        template=template
    )
    return template_message.model_dump()

def get_whatsapp_reaction_request(
    phone_number_id,
    message_id,
    reaction
):
    reaction_message = wa_requests.WhatsAppMessage(
        messaging_product="whatsapp",
        to=phone_number_id,
        type=WhatsAppMessageTypes.REACTION.value,
        reaction=wa_requests.Reaction(
            message_id=message_id,
            emoji=reaction
        )
    )
    return reaction_message.model_dump()

def get_whatsapp_read_reciept(message_id):
    read_receipt = wa_requests.WhatsAppReadMessage(
        messaging_product="whatsapp",
        status="read",
        message_id=message_id
    )
    return read_receipt.model_dump()