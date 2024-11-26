from byoeb.factory import (
    ChannelRegisterAppFactory,
    QueueProducerFactory,
    MongoDBFactory
)
from byoeb.handler import (
    ChannelRegisterHandler,
    QueueProducerHandler,
    UsersHandler
)
from byoeb.app.configuration.config import (
    env_whatsapp_phone_number_id,
    env_whatsapp_auth_token,
    app_config
)
from byoeb_integrations.channel.whatsapp.meta.async_whatsapp_client import AsyncWhatsAppClient
from byoeb.listener.message_consumer import QueueConsumer 

SINGLETON = "singleton"

channel_register_factory = ChannelRegisterAppFactory()
channel_register_handler = ChannelRegisterHandler(channel_register_factory)

whatsapp_client = AsyncWhatsAppClient(
    phone_number_id=env_whatsapp_phone_number_id,
    bearer_token=env_whatsapp_auth_token,
    reuse_client=app_config["channel"]["whatsapp"]["reuse_client"]
)

queue_producer_factory = QueueProducerFactory(
    config=app_config,
    scope = SINGLETON
)
message_producer_handler = QueueProducerHandler(
    config=app_config,
    queue_producer_factory=queue_producer_factory
)
queue_consumer = QueueConsumer(
    config=app_config,
    consuemr_type=app_config["app"]["queue_provider"]
)

mongo_db_factory = MongoDBFactory(
    config=app_config,
    scope=SINGLETON
)
users_handler = UsersHandler(
    db_provider=app_config["app"]["db_provider"],
    mongo_db_facory=mongo_db_factory
)
