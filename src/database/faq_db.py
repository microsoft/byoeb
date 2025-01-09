from embeddings.chroma.llama_index_azure_openi import get_chroma_llama_index_azure_openai_embeddings_fn
import os
import datetime
import pymongo
import certifi
import chromadb
from database.base import BaseDB
import random

from chromadb.utils import embedding_functions

from chromadb.config import Settings

class FAQDB(BaseDB):
    def __init__(self, config):
        super().__init__(config)
        self.collection = self.db[config['COSMOS_FAQ_COLLECTION']]

        self.config = config
        self.persist_directory = os.path.join(
            os.path.join(os.environ["APP_PATH"], os.environ["DATA_PATH"]), "vectordb_faq"
        )
        self.embedding_fn = get_chroma_llama_index_azure_openai_embeddings_fn()
        # self.embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
        #     api_key=os.environ['OPENAI_API_KEY'].strip(),
        #     api_type='azure',
        #     api_base=os.environ['OPENAI_API_ENDPOINT'].strip(),
        #     model_name="text-embedding-ada-002"
        # )

    def insert_row(self,
        question,
        answer,
        org_id):

        row = {
            'question': question,
            'answer': answer,
            'org_id': org_id,
            'created_at': datetime.datetime.now(),
            'updated_at': datetime.datetime.now()
        }

        db_id = self.collection.insert_one(row)

        return db_id


    def find_question(self,
        question):
        return self.collection.find_one({'question': question})


    def create_vector_index(self):
        self.client = chromadb.PersistentClient(
            path=self.persist_directory, settings=Settings(anonymized_telemetry=False)
        )
        try:
            self.client.delete_collection(
                name="FAQ",
            )
        except:
            print("Creating new collection.")
        
        self.vector_db = self.client.create_collection(
            name="FAQ",
            embedding_function=self.embedding_fn,
        )

        faqs = self.collection.find({})
        faqs = list(faqs)
        print(faqs)
        documents = [ d['question'] for d in faqs ]
        metadatas = [ { 'question': d['question'], 'answer': d['answer'], 'org_id': d['org_id'] } for d in faqs ]
        print(len(documents), len(metadatas))
        self.vector_db.add(
            ids = [ str(i) for i in range(len(documents)) ],
            documents = documents,
            metadatas = metadatas
        )

        print("FAQ DB created with {} documents.".format(self.vector_db.count()))
        return
    
    def find_closest_matches(self, query, org_id, k=10):
        client = chromadb.PersistentClient(
            path=self.persist_directory, settings=Settings(anonymized_telemetry=False)
        )

        vector_db = client.get_collection(
            name="FAQ", embedding_function=self.embedding_fn
        )
        results = vector_db.query(
            query_texts=[query],
            n_results=k,
            where={"org_id": org_id})
        return results
    
    def answer_query_faq(self,
        user_conv_db,
        db_id,
        org_id,
        logger):

        user_conv = user_conv_db.get_from_db_id(db_id)
        question = user_conv['message_english']

        faq = self.find_question(question)
        if faq is not None:
            return faq['answer'], [ f"{faq['question']} {faq['answer']}"], 'faq'
        
        top_matches = self.find_closest_matches(question, org_id)

        #TODO rerank using llm
        if len(top_matches['distances'][0]) == 0 or top_matches['distances'][0][0] > 0.2:
            return None, None, None

        print(top_matches)
        return top_matches['metadatas'][0][0]['answer'], [ f"{top_matches['metadatas'][0][0]['question']} {top_matches['metadatas'][0][0]['answer']}"], 'faq'
    
    def find_related_qns(self,
        row_query,
        response,
        org_id,
        num_questions=3):

        query = f"{row_query['message_english']} {response}"
        top_questions = self.find_closest_matches(query, org_id, k=20)

        related_qns = []

        #remove if answer same as response:
        for i in range(len(top_questions['metadatas'][0])):
            if top_questions['metadatas'][0][i]['answer'] != response:
                related_qns.append(top_questions['metadatas'][0][i])

        #for every unique answer, pick a question as random
        responses_used = {}

        #shuffle the list
        random.shuffle(related_qns)

        #remove duplicates and pick one question for each answer
        final_qns = []
        for qn in related_qns:
            if qn['answer'] not in responses_used:
                responses_used[qn['answer']] = True
                final_qns.append(qn['question'])

        final_qns.sort(key=len)

        return final_qns[:num_questions]
        
        