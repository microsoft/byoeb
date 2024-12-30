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