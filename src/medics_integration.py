import os
from datetime import datetime

import json
import yaml
from onboard import onboard_template
from pymongo import MongoClient

local_path = os.environ['APP_PATH']
import sys
sys.path.append(local_path + '/src')
with open(os.path.join(local_path,'config.yaml')) as file:    
        config = yaml.load(file, Loader=yaml.FullLoader)
from conversation_database import LoggingDatabase
from onboard import onboard_template, onboar_medics_template
from uuid import uuid4
from database import UserDB, UserConvDB, ExpertConvDB, BotConvDB, UserRelationDB
from messenger import WhatsappMessenger

class OnboardMedics:
    def __init__(self):
        self.user_db = UserDB(config)
        self.bot_conv_db = BotConvDB(config)
        self.user_relations_db = UserRelationDB(config)
        self.unit_onboarding_data = json.load(open(os.path.join(os.environ['APP_PATH'], os.environ['DATA_PATH'], 'unit_onboarding_data.json')))
        self.messenger = WhatsappMessenger(config, logger)
        

    def onboard_medics_helper(self, data):
        print('Medics data received')

        unit = data['MRD'].split('/')[0]

        assert unit in self.unit_onboarding_data, "Unit not found in unit_onboarding_data"
        assert data['surgery_name'] == "CATARACT", "Only CATARACT surgery is supported for now"

        unit_data = self.unit_onboarding_data[unit]
        unit_lang_template = unit_data['lang_template_name']
        

        
        patient_row = {
            'user_id': str(uuid4()),
            'whatsapp_id': '91'+str(data['phone_number']),
            'user_language': unit_data['language'],
            'user_type': 'Patient',
        }

        patient_meta = {
            'patient_id': data['MRD'],
            'patient_name': data['name'],
            'patient_gender': data['gender'],
            'patient_age': str(data['age']),
            'patient_surgery_date': str(data['surgery_date']),
        }

        self.user_db.insert_row(
            user_id=patient_row['user_id'],
            whatsapp_id=patient_row['whatsapp_id'],
            user_type='Patient',
            user_language=patient_row['user_language'],
            org_id=unit_data['org_id'],
            meta = patient_meta,
        )
        patient_user_id = patient_row['user_id']

        onboarding_msg_id = self.messenger.send_template(patient_row['whatsapp_id'], 'onboard_cataractbot', patient_row['user_language'])
        lang_poll_msg_id = self.messenger.send_template(patient_row['whatsapp_id'], unit_lang_template, patient_row['user_language'])

        self.bot_conv_db.insert_row(
            receiver_id=patient_user_id,
            message_type='onboarding_template',
            message_id=onboarding_msg_id,
            audio_message_id=None,
            message_source_lang=None,
            message_language=patient_row['user_language'],
            message_english=None,
            reply_id=None,
            citations=None,
            message_timestamp=datetime.now(),
            transaction_message_id=None,
        )

        self.bot_conv_db.insert_row(
            receiver_id=patient_user_id,
            message_type='lang_poll_onboarding',
            message_id=lang_poll_msg_id,
            audio_message_id=None,
            message_source_lang=None,
            message_language=patient_row['user_language'],
            message_english=None,
            reply_id=None,
            citations=None,
            message_timestamp=datetime.now(),
            transaction_message_id=None,
        )

        doctor_whatsapp_id = '91'+str(data['operating_doctor_number'])

        doctor_row = self.user_db.get_from_whatsapp_id(doctor_whatsapp_id)
        if doctor_row is None:
            doctor_row = {
                'user_id': uuid4(),
                'whatsapp_id': doctor_whatsapp_id,
                'user_language': 'en',
                'user_type': 'Doctor',
                'org_id': unit_data['org_id'],
                'user_name': data['operating_doctor'],
            }
            self.user_db.insert_row(
                user_id=doctor_row['user_id'],
                whatsapp_id=doctor_row['whatsapp_id'],
                user_type=doctor_row['user_type'],
                user_language=doctor_row['user_language'],
                org_id=doctor_row['org_id'],
                meta = {'user_name': doctor_row['user_name']}
            )

            doc_onboarding_msg_id = self.messenger.send_template(doctor_whatsapp_id, 'onboard_doctor_cataractbot', doctor_row['user_language'])

            self.bot_conv_db.insert_row(
                receiver_id=doctor_row['user_id'],
                message_type='onboarding_template',
                message_id=doc_onboarding_msg_id,
                audio_message_id=None,
                message_source_lang=None,
                message_language=doctor_row['user_language'],
                message_english=None,
                reply_id=None,
                citations=None,
                message_timestamp=datetime.now(),
                transaction_message_id=None,
            )

        doctor_user_id = doctor_row['user_id']
                 

        counsellor_row = self.user_db.collection.find_one({'user_name': data['counsellor_name']})
        counsellor_user_id = counsellor_row['user_id']

        self.user_relations_db.insert_row(
            patient_user_id, doctor_user_id, 'Patient', 'Doctor'
        )
        self.user_relations_db.insert_row(
            patient_user_id, counsellor_user_id, 'Patient', 'Counsellor'
        )

        return


    

if __name__ == "__main__":
    logger = LoggingDatabase(config)
    messenger = WhatsappMessenger(config, logger)

    onboard_medics = OnboardMedics()
    data = [{"MRD":"SEHBLR/828933/24","name":"Bhuvan","phone_number":"8375066113","surgery_name":"CATARACT","suregery_group_name":"Others","age":23,"gender":"male","procedure_type":"Major Procedure","surgery_date":"10-04-2024","operating_doctor":"MSR","operating_doctor_number":"8904954952","counsellor_name":"MSR counsellor","counsellor_number":""}]
    for row in data:
        onboard_medics.onboard_medics_helper(row)


    #sample request: [{"MRD":"SEHBLR/828933/24","name":"Bhuvan","phone_number":"8375066113","surgery_name":"CATARACT","suregery_group_name":"Others","age":23,"gender":"male","procedure_type":"Major Procedure","surgery_date":"10-04-2024","operating_doctor":"MSR","operating_doctor_number":8904954952,"counsellor_name":"MSR counsellor","counsellor_number":""}]


    #reply: Message received {"object": "whatsapp_business_account", "entry": [{"id": "145465768651550", "changes": [{"value": {"messaging_product": "whatsapp", "metadata": {"display_phone_number": "15550489892", "phone_number_id": "165481563304443"}, "contacts": [{"profile": {"name": "Bhuvan Sachdeva"}, "wa_id": "918375066113"}], "messages": [{"context": {"from": "15550489892", "id": "wamid.HBgMOTE4Mzc1MDY2MTEzFQIAERgSRjMzNzY5NDA1RjkyODcwQTY4AA=="}, "from": "918375066113", "id": "wamid.HBgMOTE4Mzc1MDY2MTEzFQIAEhggNEQ2NUM0NDZGNjVGQkU2RkRCMjI0MjdCRENENjUxNDEA", "timestamp": "1729148937", "type": "button", "button": {"payload": "\u0939\u093f\u0902\u0926\u0940", "text": "\u0939\u093f\u0902\u0926\u0940"}}]}, "field": "messages"}]}]}