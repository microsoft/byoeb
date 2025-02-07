import os
import json
from dotenv import load_dotenv

# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))
app_config_path = os.path.join(current_dir, '..', 'app_config.json')
app_config_path = os.path.normpath(app_config_path)
app_config = None
with open(app_config_path, 'r') as file:
    app_config = json.load(file)

prompt_config_path = os.path.join(current_dir, '..', 'prompts.json')
prompt_config_path = os.path.normpath(prompt_config_path)
prompt_config = None
with open(prompt_config_path, 'r') as file:
    prompt_config = json.load(file)

environment_path = os.path.join(current_dir, '../../..', 'keys.env')
environment_path = os.path.normpath(environment_path)
load_dotenv(environment_path)

# OpenAI
env_openai_api_key = os.getenv("OPENAI_API_KEY")
env_openai_org_id = os.getenv("OPENAI_ORG_ID")