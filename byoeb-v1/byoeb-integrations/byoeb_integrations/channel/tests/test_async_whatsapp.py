import os
import asyncio
import uuid
import pytest
import byoeb_core.convertor.audio_convertor as ac
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
    whatsapp_text_response = await whatsapp_client.asend_batch_messages(batch_request, message_type)
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
    template_name = "hello_world"
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
            code="en_US",
        )
    )
    batch_request = []
    for number in test_numbers:
        whatsapp_text_message = wa_template.WhatsAppTemplateMessage(
            messaging_product=whatsapp_client.get_product_name(),
            to=number,
            type=message_type,
            template=template
        )
    whatsapp_text_response = await whatsapp_client.asend_batch_messages(batch_request, message_type)
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
    audio_id = response.get("id")
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
    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(atest_batch_send_audio_message())
    # event_loop.run_until_complete(atest_meta_batch_send_template_message())
    event_loop.close()
