from byoeb.factory import (
    ChannelRegisterAppFactory, 
    QueueProducerFactory
)

from byoeb.handler import (
    ChannelRegisterHandler,
    QueueProducerHandler
)

from byoeb.app.configuration.configuration import (
    env_whatsapp_phone_number_id,
    env_whatsapp_auth_token,
    app_settings
)

from byoeb_integrations.channel.whatsapp.meta.async_whatsapp_client import AsyncWhatsAppClient
from byoeb.messaging.consumer import QueueConsumer

channel_register_factory = ChannelRegisterAppFactory()
channel_register_handler = ChannelRegisterHandler(channel_register_factory)

queue_producer_factory = QueueProducerFactory(config=app_settings)
queue_producer_handler = QueueProducerHandler(queue_producer_factory)

whatsapp_client = AsyncWhatsAppClient(
    phone_number_id=env_whatsapp_phone_number_id,
    bearer_token=env_whatsapp_auth_token,
    reuse_client=app_settings["whatsapp"]["reuse_client"]
)

queue_consumer = QueueConsumer(
    config=app_settings,
    consuemr_type="azure_storage_queue"
)

