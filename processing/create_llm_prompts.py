import json
import yaml
import os

config_path = os.path.join(os.environ["APP_PATH"], "config.yaml")
with open(config_path) as file:
    config = yaml.load(file, Loader=yaml.FullLoader)

BASE_PROMPT = '''If the query can be truthfully and factually answered using the knowledge base only, answer it concisely in a polite and professional way. If not, then just say "I do not know the answer to your question".\n\
Incase of a conflict between raw knowledge base and new knowledge base, prefer the new knowledge base.\n\
One exception to the above is if the query is a greeting or an acknowledgement or gratitude. If the query is a greeting, then respond with a greeting. \n\
If the query is an acknowledgement or gratitude to the bot's response, then respond with an acknowledgement of the same.\n\
Some examples of acknowledgement or gratitude to the bot's response are "Thank You", "Got it" and "I understand".\n'''

num = 1 + len(config['EXPERTS'])
categories = ['small-talk']
categories_str = "'small-talk'"
for expert in config['EXPERTS']:
    categories.append(config['EXPERTS'][expert])
    categories_str += f" , '{config['EXPERTS'][expert]}'"

categories_str = categories_str.replace(',', 'or')
default_category = "small-talk" if num == 1 else "any one except small-talk"

CLASSIFICATION_PROMPT = f'''In addition to the above, indicate like a {num}-class classifier if the query is {categories_str} . \n\
Here "small-talk" is defined as a query which is a greeting or an acknowledgement or gratitude. \n\
Answer it in the following json format:\n\
{{"response": <Bot response>, "query_type": {categories_str}}} \n\
Ensure that the query_type belongs to only the above mentioned {num} categories. When not sure, choose {default_category}. \n'''
llm_prompts = {}

ANSWERING_SYSTEM_PROMPT = config['USER_PROMPT'] + '\n' + BASE_PROMPT + CLASSIFICATION_PROMPT

llm_prompts['answer_query'] = ANSWERING_SYSTEM_PROMPT

CORRECTION_SYSTEM_PROMPT = f'''{config['USER_PROMPT']}. \
A user asked a query and the chatbot answered it. But, the expert gives a correction to the chatbot's response.\n\
Update the chatbot's response by taking the expert's correction into account. Respond only with the final updated response.\n\
'''

llm_prompts['generate_correction'] = CORRECTION_SYSTEM_PROMPT

FOLLOW_UP_PROMPT = f''' What are three possible follow-up questions the user might ask? \
Respond with the questions only in a python list of strings. Each question should not exceed 72 characters.\
'''

llm_prompts['follow_up_questions'] = FOLLOW_UP_PROMPT








print(repr(llm_prompts))


save_path = os.path.join(os.environ["APP_PATH"], os.environ['DATA_PATH'], "llm_prompt.json")
with open(save_path, "w") as fp:
    json.dump(llm_prompts, fp)
