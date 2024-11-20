import os
import json
from dotenv import load_dotenv

# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))
settings_path = os.path.join(current_dir, '..', 'settings.json')
settings_path = os.path.normpath(settings_path)
app_settings = None
with open(settings_path, 'r') as file:
    app_settings = json.load(file)   

environment_path = os.path.join(current_dir, '../../..', 'keys.env')
environment_path = os.path.normpath(environment_path)
load_dotenv(environment_path)
# Environment variables
env_whatsapp_token = os.getenv("WHATSAPP_VERIFICATION_TOKEN")
env_whatsapp_auth_token = os.getenv("WHATSAPP_AUTH_TOKEN")
env_whatsapp_phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")