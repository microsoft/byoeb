import uuid
from byoeb_core.models.whatsapp.response.message_response import (
    WhatsAppResponse,
    WhatsAppResponseStatus,
    Contact,
    Message
)

def get_mock_whatsapp_response(
    phone_number_id: str,
):
    return WhatsAppResponse(
        messaging_product="whatsapp",
        response_status=WhatsAppResponseStatus(
            status='200'
        ),
        contacts=[
            Contact(
                input=phone_number_id,
                wa_id=phone_number_id
            )
        ],
        messages=[
            Message(
                id=str(uuid.uuid4()),
            )
        ],
        media_message=None
    )