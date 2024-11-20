import os
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
environment_path = os.path.join(current_dir, 'keys.env')
environment_path = os.path.normpath(environment_path)
load_dotenv(environment_path)
env_whatsapp_token = os.getenv("WHATSAPP_VERIFICATION_TOKEN")
print(f"env_whatsapp_token: {env_whatsapp_token}")
env_whatsapp_auth_token = os.getenv("WHATSAPP_AUTH_TOKEN")
print(f"env_whatsapp_auth_token: {env_whatsapp_auth_token}")
env_whatsapp_phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
print(f"env_whatsapp_phone_number_id: {env_whatsapp_phone_number_id}")