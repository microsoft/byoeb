import os
import asyncio
import uuid
import pytest
import byoeb_core.convertor.audio_convertor as ac
import json
import byoeb_integrations.channel.whatsapp.validate_message as wa_validate
import byoeb_integrations.channel.whatsapp.convert_message as wa_convert
from byoeb_core.models.whatsapp.requests import message_request as wa_message
from byoeb_core.models.whatsapp.requests import interactive_message_request as wa_interactive
from byoeb_core.models.whatsapp.requests import template_message_request as wa_template
from byoeb_core.models.whatsapp.requests import media_request as wa_media
from byoeb_core.models.whatsapp.message_context import WhatsappMessageReplyContext
from byoeb_integrations.channel.whatsapp.meta.async_whatsapp_client import AsyncWhatsAppClient, WhatsAppMessageTypes
from byoeb_integrations import test_environment_path
from dotenv import load_dotenv

load_dotenv(test_environment_path)
WHATSAPP_AUTH_TOKEN = os.getenv('WHATSAPP_AUTH_TOKEN')
WHATSAPP_PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID')

@pytest.fixture(scope="session")
def event_loop():
    """Create and reuse a single event loop for all tests in the session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop

test_numbers = ["918837701828", "918904954952"]

async def atest_meta_batch_text_message():
    whatsapp_client = AsyncWhatsAppClient(
        phone_number_id=WHATSAPP_PHONE_NUMBER_ID,
        bearer_token=WHATSAPP_AUTH_TOKEN,
        reuse_client=True
    )
    message_type = WhatsAppMessageTypes.TEXT.value
    text_message = "Hello how are you"
    text = wa_message.Text(body=text_message)
    batch_request = []
    for number in test_numbers:
        whatsapp_text_message = wa_message.WhatsAppMessage(
            messaging_product=whatsapp_client.get_product_name(),
            to=number,
            type=message_type,
            text=text
        )
        batch_request.append(whatsapp_text_message.model_dump())
    batch_reponses = await whatsapp_client.asend_batch_messages(batch_request, message_type)
    
    batch_reaction_request = []
    for response in batch_reponses:
        assert response is not None
        if (response.response_status.status != "202" 
            and response.response_status.status != "200"
        ):
            continue
        message_id = response.messages[0].id
        contact = response.contacts[0].wa_id
        whatsapp_text_message = wa_message.WhatsAppMessage(
            messaging_product=whatsapp_client.get_product_name(),
            to=contact,
            type=WhatsAppMessageTypes.REACTION.value,
            reaction=wa_message.Reaction(
                message_id=message_id,
                emoji="👍"
            )
        )
        batch_reaction_request.append(whatsapp_text_message.model_dump())
    
    batch_reaction_response = await whatsapp_client.asend_batch_messages(batch_reaction_request, WhatsAppMessageTypes.REACTION.value)

    batch_reply_request = []
    for response in batch_reponses:
        assert response is not None
        if (response.response_status.status != '202' 
            and response.response_status.status != '200'
        ):
            continue
        message_id = response.messages[0].id
        contact = response.contacts[0].wa_id
        whatsapp_text_message = wa_message.WhatsAppMessage(
            messaging_product=whatsapp_client.get_product_name(),
            to=contact,
            type=WhatsAppMessageTypes.TEXT.value,
            text=wa_message.Text(body="I am fine, thank you!"),
            context=WhatsappMessageReplyContext(
                message_id=message_id
            )
        )
        batch_reply_request.append(whatsapp_text_message.model_dump(by_alias=True))
    batch_reply_response = await whatsapp_client.asend_batch_messages(batch_reply_request, message_type)
    await whatsapp_client._close()
    
async def atest_meta_batch_send_interactive_reply_message():
    
    def get_button(title):
        poll_id = str(uuid.uuid4())
        return wa_interactive.InteractiveActionButton(
            reply=wa_interactive.InteractiveReply(
                id=poll_id,
                title=title
            )
        )
    whatsapp_client = AsyncWhatsAppClient(
        phone_number_id=WHATSAPP_PHONE_NUMBER_ID,
        bearer_token=WHATSAPP_AUTH_TOKEN,
        reuse_client=True
    )
    message_type = WhatsAppMessageTypes.INTERACTIVE.value
    batch_request = []
    for number in test_numbers:
        whatsapp_text_message = wa_interactive.WhatsAppInteractiveMessage(
            messaging_product=whatsapp_client.get_product_name(),
            to=number,
            type=message_type,
            interactive=wa_interactive.Interactive(
                body=wa_interactive.InteractiveBody(
                    text="Do you like this product?"
                ),
                action=wa_interactive.InteractiveAction(
                    buttons=[get_button("Yes"), get_button("No")]
                )
            )
        )
        print(json.dumps(whatsapp_text_message.model_dump(exclude_none=True)))
        batch_request.append(whatsapp_text_message.model_dump())
    # whatsapp_text_response = await whatsapp_client.asend_batch_messages(batch_request, message_type)
    await whatsapp_client._close()

async def atest_meta_batch_send_interactive_list_message():
    def get_section(description):
        return wa_interactive.InteractiveActionSection(
            title=description,
            rows=[
                get_section_row("O1"),
                get_section_row("O2"),
                get_section_row("O3")
            ]
        )

    def get_section_row(description):
        return wa_interactive.InteractiveSectionRow(
            id=str(uuid.uuid4()),
            title=" ",
            description=description
        )
    whatsapp_client = AsyncWhatsAppClient(
        phone_number_id=WHATSAPP_PHONE_NUMBER_ID,
        bearer_token=WHATSAPP_AUTH_TOKEN,
        reuse_client=True
    )
    batch_request = []
    for number in test_numbers:
        message_type = WhatsAppMessageTypes.INTERACTIVE.value
        interactive_type = wa_interactive.InteractiveMessageTypes.LIST.value
        whatsapp_text_message = wa_interactive.WhatsAppInteractiveMessage(
            messaging_product=whatsapp_client.get_product_name(),
            to=number,
            type=message_type,
            interactive=wa_interactive.Interactive(
                type=interactive_type,
                body=wa_interactive.InteractiveBody(
                    text="Select an option"
                ),
                action=wa_interactive.InteractiveAction(
                    button="Button Options",
                    sections=[
                        get_section("S1"),
                    ]
                )
            )
        )
        batch_request.append(whatsapp_text_message.model_dump())

    whatsapp_text_response = await whatsapp_client.asend_batch_messages(batch_request, message_type)
    await whatsapp_client._close()

async def atest_meta_batch_send_template_message():
    whatsapp_client = AsyncWhatsAppClient(
        phone_number_id=WHATSAPP_PHONE_NUMBER_ID,
        bearer_token=WHATSAPP_AUTH_TOKEN,
        reuse_client=True
    )
    template_name = "question_of_the_week"
    text = "नवजात शिशु के शरीर में 300 हड्डियाँ होती हैं।"
    message_type = WhatsAppMessageTypes.TEMPLATE.value
    component = wa_template.TemplateComponent(
        type="body",
        parameters=[
            wa_template.TemplateParameter(
                type="text",
                text=text
            )
        ]
    )
    template = wa_template.Template(
        name =template_name,
        language=wa_template.TemplateLanguage(
            code="hi",
        ),
        components=[component]
    )
    batch_request = []
    for number in test_numbers:
        whatsapp_text_message = wa_template.WhatsAppTemplateMessage(
            messaging_product=whatsapp_client.get_product_name(),
            to=number,
            type=message_type,
            template=template
        )
        batch_request.append(whatsapp_text_message.model_dump())
        print(json.dumps(whatsapp_text_message.model_dump(exclude_none=True)))
    whatsapp_text_response = await whatsapp_client.asend_batch_messages(batch_request, message_type)
    assert whatsapp_text_response is not None
    assert whatsapp_text_response[0].response_status.status == "200"
    await whatsapp_client._close()

async def atest_audio_download():
    whatsapp_client = AsyncWhatsAppClient(
        phone_number_id=WHATSAPP_PHONE_NUMBER_ID,
        bearer_token=WHATSAPP_AUTH_TOKEN,
        reuse_client=True
    )
    message_type = wa_media.WhatsAppMediaTypes.AUDIO.value
    audio_bytes = ac.text_to_wav_bytes("Hello, how are you?")
    audio_bytes = ac.wav_to_ogg_opus_bytes(audio_bytes)
    media_type=wa_media.FileMediaType.AUDIO_OGG.value
    status, response, err = await whatsapp_client._upload_media(audio_bytes, media_type)
    audio_id = '1593203484905159'
    status, audio_data, err = await whatsapp_client.adownload_media(audio_id)
    assert audio_data.data is not None
    ack = await whatsapp_client.adelete_media(audio_id)
    assert ack.success is True
    await whatsapp_client._close()

async def atest_mark_as_read():
    whatsapp_client = AsyncWhatsAppClient(
        phone_number_id=WHATSAPP_PHONE_NUMBER_ID,
        bearer_token=WHATSAPP_AUTH_TOKEN,
        reuse_client=True
    )
    id = "wamid.HBgMOTE4ODM3NzAxODI4FQIAEhggODdBQjNFNTFBQzRCNEY1MjU1QTcwMEI4RTRBNkNGQUEA"
    ack = await whatsapp_client.amark_as_read(id)
    assert ack.success is True
    await whatsapp_client._close()

async def atest_batch_send_audio_message():
    message_type = wa_media.WhatsAppMediaTypes.AUDIO.value
    audio_wav = None
    with open("audio.wav", "rb") as f:
        audio_wav = f.read()
    audio_bytes = ac.wav_to_ogg_opus_bytes(audio_wav)
    media_type=wa_media.FileMediaType.AUDIO_OGG.value
    whatsapp_client = AsyncWhatsAppClient(
        phone_number_id=WHATSAPP_PHONE_NUMBER_ID,
        bearer_token=WHATSAPP_AUTH_TOKEN,
        reuse_client=True
    )
    batch_request = []
    for number in test_numbers:
        whatsapp_media_message = wa_media.WhatsAppMediaMessage(
            messaging_product=whatsapp_client.get_product_name(),
            to=number,
            type=message_type,
            media=wa_media.MediaData(
                data=audio_bytes,
                mime_type=media_type
            )
        )
        batch_request.append(whatsapp_media_message.model_dump())
    whatsapp_responses = await whatsapp_client.asend_batch_messages(batch_request, message_type)
    media_id = whatsapp_responses[0].media_message.id
    ack = await whatsapp_client.adelete_media(media_id)
    assert ack.success is True
    await whatsapp_client._close()

def test_template_message():
    message = '{"object": "whatsapp_business_account", "entry": [{"id": "423299570870294", "changes": [{"value": {"messaging_product": "whatsapp", "metadata": {"display_phone_number": "15551355272", "phone_number_id": "421395191063010"}, "contacts": [{"profile": {"name": "rahul5982439"}, "wa_id": "918837701828"}], "messages": [{"context": {"from": "15551355272", "id": "wamid.HBgMOTE4ODM3NzAxODI4FQIAERgSRjZCQThENDNGREY0MjdEMTczAA=="}, "from": "918837701828", "id": "wamid.HBgMOTE4ODM3NzAxODI4FQIAEhggQTNDMDU5QzQwMUNBOUQyMDM4OTAxQTZGQUFFNUE1RDEA", "timestamp": "1732167477", "type": "button", "button": {"payload": "\u0909\u0924\u094d\u0924\u0930 \u0926\u093f\u0916\u093e\u0907\u090f", "text": "\u0909\u0924\u094d\u0924\u0930 \u0926\u093f\u0916\u093e\u0907\u090f"}}]}, "field": "messages"}]}]}'
    is_wa, message_type = wa_validate.validate_whatsapp_message(message)
    wa_convert.convert_template_message(message)
    assert is_wa is True
    assert message_type == "template"

def test_regular_message():
    message_1 = '{"object": "whatsapp_business_account", "entry": [{"id": "423299570870294", "changes": [{"value": {"messaging_product": "whatsapp", "metadata": {"display_phone_number": "15551355272", "phone_number_id": "421395191063010"}, "contacts": [{"profile": {"name": "rahul5982439"}, "wa_id": "918837701828"}], "messages": [{"from": "918837701828", "id": "wamid.HBgMOTE4ODM3NzAxODI4FQIAEhggMTU1NEI5QjRBNTlCNUZCQTk0QzlBNDY2NDRDNEYyMzkA", "timestamp": "1732167417", "text": {"body": "Hello"}, "type": "text"}]}, "field": "messages"}]}]}'
    is_wa, message_type = wa_validate.validate_whatsapp_message(message_1)
    wa_convert.convert_regular_message(message_1)
    assert is_wa is True
    assert message_type == "regular"
    message_2 = '{"object": "whatsapp_business_account", "entry": [{"id": "423299570870294", "changes": [{"value": {"messaging_product": "whatsapp", "metadata": {"display_phone_number": "15551355272", "phone_number_id": "421395191063010"}, "contacts": [{"profile": {"name": "rahul5982439"}, "wa_id": "918837701828"}], "messages": [{"from": "918837701828", "id": "wamid.HBgMOTE4ODM3NzAxODI4FQIAEhggNEJFQzc1OEFBNTlDQTQxOTI2MDQ3RTNGM0E4OTQxRDEA", "timestamp": "1732167457", "type": "audio", "audio": {"mime_type": "audio/ogg; codecs=opus", "sha256": "w26HXHrAYkyu19h0AStMV+9ojTl5mQwAQmBHPedekX0=", "id": "543799451804859", "voice": true}}]}, "field": "messages"}]}]}'
    is_wa, message_type = wa_validate.validate_whatsapp_message(message_2)
    wa_convert.convert_regular_message(message_2)
    assert is_wa is True
    assert message_type == "regular"

def test_interactive_message():
    message_1 = '{"object": "whatsapp_business_account", "entry": [{"id": "423299570870294", "changes": [{"value": {"messaging_product": "whatsapp", "metadata": {"display_phone_number": "15551355272", "phone_number_id": "421395191063010"}, "contacts": [{"profile": {"name": "rahul5982439"}, "wa_id": "918837701828"}], "messages": [{"context": {"from": "15551355272", "id": "wamid.HBgMOTE4ODM3NzAxODI4FQIAERgSNkY1QUIwQTMzNjc2MkU1OUZGAA=="}, "from": "918837701828", "id": "wamid.HBgMOTE4ODM3NzAxODI4FQIAEhggODg4REFBQUI4NzM1NUI1MDc2NjA2ODMwQjFFQkU3QzUA", "timestamp": "1732167674", "type": "interactive", "interactive": {"type": "button_reply", "button_reply": {"id": "804dcad1-def3-4e37-b391-9aa51fe7f5c3", "title": "Yes"}}}]}, "field": "messages"}]}]}'
    is_wa, message_type = wa_validate.validate_whatsapp_message(message_1)
    wa_convert.convert_interactive_message(message_1)
    assert is_wa is True
    assert message_type == "interactive"
    message_2 = '{"object": "whatsapp_business_account", "entry": [{"id": "423299570870294", "changes": [{"value": {"messaging_product": "whatsapp", "metadata": {"display_phone_number": "15551355272", "phone_number_id": "421395191063010"}, "contacts": [{"profile": {"name": "rahul5982439"}, "wa_id": "918837701828"}], "messages": [{"context": {"from": "15551355272", "id": "wamid.HBgMOTE4ODM3NzAxODI4FQIAERgSMzU5QTYwNzNBQUUzNjdDNjAwAA=="}, "from": "918837701828", "id": "wamid.HBgMOTE4ODM3NzAxODI4FQIAEhggNURBMjI2MUI1REREOUU1RTk0OTRDNzY4NkJEMjQxM0UA", "timestamp": "1732167786", "type": "interactive", "interactive": {"type": "list_reply", "list_reply": {"id": "f79a74e4-3d50-4cc3-ae50-86efff88f3f3", "title": " ", "description": "O1"}}}]}, "field": "messages"}]}]}'
    is_wa, message_type = wa_validate.validate_whatsapp_message(message_2)
    byoeb_message = wa_convert.convert_interactive_message(message_2)
    assert byoeb_message.reply_context.reply_id == "wamid.HBgMOTE4ODM3NzAxODI4FQIAERgSMzU5QTYwNzNBQUUzNjdDNjAwAA=="
    assert is_wa is True
    assert message_type == "interactive"

def test_status_message():
    message = '{"object": "whatsapp_business_account", "entry": [{"id": "423299570870294", "changes": [{"value": {"messaging_product": "whatsapp", "metadata": {"display_phone_number": "15551355272", "phone_number_id": "421395191063010"}, "statuses": [{"id": "wamid.HBgMOTE4ODM3NzAxODI4FQIAERgSQjM1RjY0M0QyMkU4OUU3OTc3AA==", "status": "delivered", "timestamp": "1733170072", "recipient_id": "918837701828", "conversation": {"id": "bbc3027b762dec0714d75f270a6e9e9e", "origin": {"type": "service"}}, "pricing": {"billable": true, "pricing_model": "CBP", "category": "service"}}]}, "field": "messages"}]}]}'
    is_wa, message_type = wa_validate.validate_whatsapp_message(message)
    byoeb_message = wa_convert.convert_status_message(message)
    json_data = byoeb_message.model_dump_json()
    assert is_wa is True
    assert byoeb_message.message_id == "wamid.HBgMOTE4ODM3NzAxODI4FQIAERgSQjM1RjY0M0QyMkU4OUU3OTc3AA=="
    assert message_type == "status"

import byoeb_integrations.channel.whatsapp.request_payload as wa_request_payload
from byoeb_core.models.byoeb.message_context import ByoebMessageContext
def test_text_request_payload():
    byoeb_message = '{"channel_type": "whatsapp", "message_category": "Bot_to_user_response", "user": {"user_id": "6dfd0676f602bdf2cd545160efd99e01", "user_name": null, "user_region": null, "user_language": "en", "user_type": "byoebuser", "phone_number_id": "918837701828", "test_user": false, "experts": ["918904954952"], "audience": [], "created_timestamp": 1732451468, "activity_timestamp": 1732451468}, "message_context": {"message_id": null, "message_type": "regular_text", "message_source_text": "Hello! How can I assist you today?", "message_english_text": "Hello! How can I assist you today?", "media_info": null, "additional_info": null}, "reply_context": {"reply_id": "wamid.HBgMOTE4ODM3NzAxODI4FQIAEhggNzc0MUZCRkREOTEzNEY4NkRENURCRDMzOTQ1MEYyNzQA", "reply_type": "regular_text", "reply_source_text": "Hi", "reply_english_text": "Hi", "media_info": null, "additional_info": null}, "cross_conversation_id": null, "cross_conversation_context": null, "incoming_timestamp": null, "outgoing_timestamp": null}'
    byoeb_message = ByoebMessageContext.model_validate(json.loads(byoeb_message))
    payload = wa_request_payload.get_whatsapp_text_request_from_byoeb_message(byoeb_message)
    print(json.dumps(payload))

def test_meta_batch_text_message(event_loop):
    event_loop.run_until_complete(atest_meta_batch_text_message())

def test_meta_batch_send_interactive_reply_message(event_loop):
    event_loop.run_until_complete(atest_meta_batch_send_interactive_reply_message())

def test_meta_batch_send_interactive_list_message(event_loop):
    event_loop.run_until_complete(atest_meta_batch_send_interactive_list_message())

def test_meta_batch_send_template_message(event_loop):
    event_loop.run_until_complete(atest_meta_batch_send_template_message())

def test_batch_send_audio_message(event_loop):
    event_loop.run_until_complete(atest_batch_send_audio_message())

def test_audio_download(event_loop):
    event_loop.run_until_complete(atest_audio_download())

if __name__ == "__main__":
    # event_loop = asyncio.get_event_loop()
    # # event_loop.run_until_complete(atest_meta_batch_send_interactive_reply_message())
    # event_loop.run_until_complete(atest_meta_batch_send_template_message())
    # event_loop.close()
    # test_template_message()
    # test_regular_message()
    # test_interactive_message()
    test_status_message()
    # asyncio.run(atest_audio_download())

