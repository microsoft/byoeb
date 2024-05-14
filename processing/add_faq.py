import os
import sys
import yaml
from collections import defaultdict

with open('config.yaml', 'r') as f:
    config = yaml.load(f, Loader=yaml.Loader)

sys.path.append('src/')


from database import UserDB, UserConvDB, BotConvDB, ExpertConvDB, UserRelationDB, FAQDB

# user_conv_db = UserConvDB(config)
# bot_conv_db = BotConvDB(config)
# expert_conv_db = ExpertConvDB(config)

faq_db = FAQDB(config)

faq_db.collection.delete_many({})

import pandas as pd

organization_dir = os.path.join(os.path.join(os.environ["APP_PATH"], os.environ["DATA_PATH"], "documents"))
orgs = os.listdir(organization_dir)

for org in orgs:
    faq_csv_path = os.path.join(organization_dir, org, "faq.csv")
    df_aug = pd.read_csv(faq_csv_path, delimiter=';')
    print(df_aug.columns)
    faq_db.collection.delete_many({})
    for i, row in df_aug.iterrows():
        faq_db.insert_row(row['Question'], row['Answer'], org)
    
faq_db.create_vector_index()