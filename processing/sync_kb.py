def kb_sync():
    import psutil
    import yaml

    import os
    print('Code started running')
    local_path = os.environ['APP_PATH']
    import sys
    sys.path.append(local_path + '/src')
    from knowledge_base import KnowledgeBase
    from conversation_database import LoggingDatabase
    import pandas as pd
    import ast
    from typing import Any
    from tqdm import tqdm
    from datetime import datetime

    with open(os.path.join(local_path,'config.yaml')) as file:    
        config = yaml.load(file, Loader=yaml.FullLoader)

    

    os.makedirs(os.path.join(local_path, os.environ['DATA_PATH'], "kb_update_raw"), exist_ok=True)
    open(os.path.join(local_path, os.environ['DATA_PATH'], "kb_update_raw/KB Updated.txt"), "w").close()
    myfile = open(os.path.join(local_path, os.environ['DATA_PATH'], "kb_update_raw/KB Updated.txt"), "a")
    rawfile = open(os.path.join(local_path, os.environ['DATA_PATH'], "raw_documents/KB Updated.txt"), "a")

    logger = LoggingDatabase(config)
    kb_updates = logger.collection.find({'$and' : [{'action_type': 'Updating KnowledgeBase'}]})
    kb_updates = pd.DataFrame(list(kb_updates))
    #make details column a dictionary
    # kb_updates['details'] = kb_updates['details']
    a = kb_updates['details'].iloc[0]
    
    kb_updates['query'] = kb_updates['details'].apply(lambda x: x['query'])
    kb_updates['updated_response'] = kb_updates['details'].apply(lambda x: x['updated_response'])
    
    for i in tqdm(range(len(kb_updates))):
        query = kb_updates['query'][i]
        updated_response = kb_updates['updated_response'][i]
        myfile.write(f'* {query.strip()}\n{updated_response.strip()}\n\n')
        rawfile.write(f'* {query.strip()}\n{updated_response.strip()}\n\n')
    
    
    myfile.close()
    rawfile.close()

    if not kb_updates.empty:
        knowledge_base = KnowledgeBase(config)
        print(repr(knowledge_base.config['PROJECT_NAME']))
        knowledge_base.create_embeddings()
        print('KB updated successfully')


    

if __name__ == "__main__":
    kb_sync()
