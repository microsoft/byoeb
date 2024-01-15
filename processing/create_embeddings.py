import yaml
import os

print("Code started running")
local_path = os.environ["APP_PATH"]
print(local_path)
import sys

sys.path.append(local_path + "/src")
from knowledge_base import KnowledgeBase

print(os.path.join(local_path, "config.yaml"))

with open(os.path.join(local_path, "config.yaml")) as file:
    config = yaml.load(file, Loader=yaml.FullLoader)


knowledge_base = KnowledgeBase(config)
knowledge_base.create_embeddings()
