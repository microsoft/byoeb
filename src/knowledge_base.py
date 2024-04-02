import os
import shutil
import sys
__import__("pysqlite3")
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")

import chromadb
import json

from conversation_database import (
    ConversationDatabase,
    LongTermDatabase,
    LoggingDatabase,
)
from database import UserConvDB
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import DirectoryLoader
from chromadb.utils import embedding_functions
import shutil
from typing import Any
from chromadb.config import Settings
from utils import get_llm_response
from datetime import datetime


class KnowledgeBase:
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.persist_directory = os.path.join(
            os.path.join(os.environ["APP_PATH"], os.environ["DATA_PATH"]), "vectordb"
        )
        self.embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.environ['OPENAI_API_KEY'].strip(),
            api_type='azure',
            api_base=os.environ['OPENAI_API_ENDPOINT'].strip(),
            model_name="text-embedding-ada-002"
        )
        
        self.llm_prompts = json.load(open(os.path.join(os.environ["APP_PATH"], os.environ["DATA_PATH"], "llm_prompt.json")))

    def answer_query(
        self,
        user_conv_db: UserConvDB,
        msg_id: str,
        logger: LoggingDatabase,
    ) -> tuple[str, str]:
        """answer the user's query using the knowledge base and chat history
        Args:
            query (str): the query
            llm (OpenAI): any foundational model
            database (Any): the database
            db_id (str): the database id of the row with the query
        Returns:
            tuple[str, str]: the response and the citations
        """

        if self.config["API_ACTIVATED"] is False:
            gpt_output = "API not activated"
            citations = "NA-API"
            query_type = "small-talk"
            return (gpt_output, citations, query_type)
        

        client = chromadb.PersistentClient(
            path=self.persist_directory, settings=Settings(anonymized_telemetry=False)
        )

        collection = client.get_collection(
            name=self.config["PROJECT_NAME"], embedding_function=self.embedding_fn
        )
        collection_count = collection.count()
        print('collection ids count: ', collection_count)

        db_row = user_conv_db.get_from_message_id(msg_id)
        query = db_row["message_english"]
        if not query.endswith("?"):
            query += "?"

        relevant_chunks = collection.query(
            query_texts=[query],
            n_results=3, 
        )
        citations: str = "\n".join(
            [metadata["source"] for metadata in relevant_chunks["metadatas"][0]]
        )

        relevant_chunks_string = ""
        relevant_update_chunks_string = ""
        chunks = []

        chunk1 = 0
        chunk2 = 0
        for chunk, chunk_text in enumerate(relevant_chunks["documents"][0]):
            if relevant_chunks["metadatas"][0][chunk]["source"].strip() == "KB Updated":
                relevant_update_chunks_string += (
                    f"Chunk #{chunk2 + 1}\n{chunk_text}\n\n"
                )
                chunk2 += 1
                chunks.append((chunk_text, relevant_chunks["metadatas"][0][chunk]["source"].strip()))
            else:
                relevant_chunks_string += f"Chunk #{chunk1 + 1}\n{chunk_text}\n\n"
                chunk1 += 1
                chunks.append((chunk_text, relevant_chunks["metadatas"][0][chunk]["source"].strip()))

        logger.add_log(
            sender_id="bot",
            receiver_id="bot",
            message_id=None,
            action_type="get_citations",
            details={"query": query, "chunks": chunks, "transaction_id": db_row["message_id"]},
            timestamp=datetime.now(),
        )

        # take all non empty conversations 
        all_conversations = user_conv_db.get_all_user_conv(db_row["user_id"])
        conversation_string = ""
        # "\n".join(
        #     [
        #         row["query"] + "\n" + row["response"]
        #         for row in all_conversations
        #         if row["response"]
        #     ][-3:]
        # )

        system_prompt = self.llm_prompts["answer_query"]
        query_prompt = f"""
            Today's date is {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\
            
            The following knowledge base chunks have been provided to you as reference:\n\n\
            Raw documents are as follows:\n\
            {relevant_chunks_string}\n\n\
            New documents are as follows:\n\
            {relevant_update_chunks_string}\n\n\
            The most recent conversations are here:\n\n\
            {conversation_string}\n\
            You are asked the following query:\n\n\
            "{query}"\n\n\

        """

        prompt = [{"role": "system", "content": system_prompt}]
        prompt.append({"role": "user", "content": query_prompt})
        logger.add_log(
            sender_id="bot",
            receiver_id="gpt4",
            message_id=None,
            action_type="answer_query_request",
            details={
                "system_prompt": system_prompt,
                "query_prompt": query_prompt,
                "transaction_id": db_row["message_id"],
            },
            timestamp=datetime.now(),
        )
        gpt_output = get_llm_response(prompt)
        logger.add_log(
            sender_id="gpt4",
            receiver_id="bot",
            message_id=None,
            action_type="answer_query_response",
            details={
                "system_prompt": system_prompt,
                "query_prompt": query_prompt,
                "gpt_output": gpt_output,
                "transaction_id": db_row["message_id"],
            },
            timestamp=datetime.now(),
        )

        json_output = json.loads(gpt_output.strip())
        bot_response = json_output["response"]
        query_type = json_output["query_type"]

        # print('bot response: ', bot_response, 'query type: ', query_type)

        if len(bot_response) < 700:
            return (bot_response, citations, query_type)
        else:
            system_prompt = f"""Please summarise the given answer in 700 characters or less. Only return the summarized answer and nothing else.\n"""
            
            query_prompt = f"""You are given the following response: {bot_response}"""
            prompt = [{"role": "system", "content": system_prompt}]
            prompt.append({"role": "user", "content": query_prompt})
            logger.add_log(
                sender_id="bot",
                receiver_id="gpt4",
                message_id=None,
                action_type="answer_summary_request",
                details={
                    "system_prompt": system_prompt,
                    "query_prompt": query_prompt,
                    "transaction_id": db_row["message_id"],
                },
                timestamp=datetime.now(),
            )

            gpt_output = get_llm_response(prompt)

            logger.add_log(
                sender_id="gpt4",
                receiver_id="bot",
                message_id=None,
                action_type="answer_summary_response",
                details={
                    "system_prompt": system_prompt,
                    "query_prompt": query_prompt,
                    "gpt_output": gpt_output,
                    "transaction_id": db_row["message_id"],
                },
                timestamp=datetime.now(),
            )
            return (gpt_output, citations, query_type)

    def generate_correction(
        self,
        row_query: dict[str, Any],
        row_response: dict[str, Any],
        row_correction: dict[str, Any],
        logger: LoggingDatabase,
    ):
        
        if self.config["API_ACTIVATED"] is False:
            gpt_output = "API not activated"
            return gpt_output

        system_prompt = self.llm_prompts["generate_correction"]
        query = row_query["message_english"]
        response = row_response["message_english"]
        correction = row_correction["message"]
        query_prompt = f"""
        A user asked the following query:\n\
                "{query}"\n\
            A chatbot answered the following:\n\
            "{response}"\n\
            An expert corrected the response as follows:\n\
            "{correction}"\n\

        """
        transaction_message_id = row_query["message_id"]
        logger.add_log(
            sender_id="bot",
            receiver_id="bot",
            message_id=None,
            action_type="get_correction",
            details={"system_prompt": system_prompt, "query_prompt": query_prompt, "transaction_message_id": transaction_message_id},
            timestamp=datetime.now(),
        )

        prompt = [{"role": "system", "content": system_prompt}]
        prompt.append({"role": "user", "content": query_prompt})

        gpt_output = get_llm_response(prompt)

        if len(gpt_output) < 700:
            return gpt_output
        else:
            system_prompt = f"""Please summarise the provided answer in 700 characters or less. Only return the summarized answer and nothing else.\n"""
            query_prompt = f"""You are given the following response: {gpt_output}"""
            prompt = [{"role": "system", "content": system_prompt}]
            prompt.append({"role": "user", "content": query_prompt})

            logger.add_log(
                sender_id="bot",
                receiver_id="bot",
                message_id=None,
                action_type="gpt4",
                details={"system_prompt": system_prompt, "query_prompt": query_prompt},
                timestamp=datetime.now(),
            )
            gpt_output = get_llm_response(prompt)

            return gpt_output

    def follow_up_questions(
        self,
        query: str,
        response: str,
        user_type: str,
        logger: LoggingDatabase,
    ) -> list[str]:
        """look at the chat history and suggest follow up questions

        Args:
            query (str): the query
            response (str): the response from the bot
            llm (OpenAI): an OpenAI model

        Returns:
            list[str]: a list of potential follow up questions
        """

        if self.config["API_ACTIVATED"] is False:
            print("API not activated")
            return ["Q1", "Q2", "Q3"]

        system_prompt = self.llm_prompts["follow_up_questions"]
        query_prompt = f"""
            A user asked the following query:\n\
                    "{query}"\n\
                A chatbot answered the following:\n\
                "{response}"\n\
            """

        prompt = [{"role": "system", "content": system_prompt}]
        prompt.append({"role": "user", "content": query_prompt})

        llm_out = get_llm_response(prompt)
        next_questions = eval(llm_out.strip("\n"))

        logger.add_log(
            sender_id="bot",
            receiver_id="bot",
            message_id=None,
            action_type="gpt4",
            details={
                "system_prompt": system_prompt,
                "query_prompt": query_prompt,
                "gpt_output": llm_out,
            },
            timestamp=datetime.now(),
        )

        return next_questions

    def update_kb_wa(self):
        client = chromadb.PersistentClient(
            path=self.persist_directory, settings=Settings(anonymized_telemetry=False)
        )

        collection = client.get_collection(
            name=self.config["PROJECT_NAME"], embedding_function=self.embedding_fn
        )

        collection_count = collection.count()
        print("collection ids count: ", collection_count)
        self.documents = DirectoryLoader(
            os.path.join(
                os.path.join(os.environ["APP_PATH"], os.environ["DATA_PATH"]),
                "kb_update_raw",
            ),
            glob=self.config["GLOB_SUFFIX"],
        ).load()
        self.texts = []
        self.sources = []
        for document in self.documents:
            next_text = RecursiveCharacterTextSplitter(chunk_size=1000).split_text(
                document.page_content
            )  # list of chunks
            self.texts.extend(next_text)
            self.sources.extend(
                [
                    document.metadata["source"].split("/")[-1][:-4]
                    for _ in range(len(next_text))
                ]
            )

        # if os.path.exists(self.persist_directory):
        #     shutil.rmtree(self.persist_directory)
        self.texts = [text.replace("\n\n", "\n") for text in self.texts]

        ids = []
        for index in range(len(self.texts)):
            ids.append([str(index + collection_count)])

        print("ids: ", ids)

        metadatas = []
        for source in self.sources:
            metadatas.append({"source": source})

        print("metadatas: ", metadatas)

        print("texts: ", self.texts)
        collection.add(
            ids=[str(index + collection_count) for index in range(len(self.texts))],
            metadatas=[{"source": source} for source in self.sources],
            documents=self.texts,
        )

        client = chromadb.PersistentClient(
            path=self.persist_directory, settings=Settings(anonymized_telemetry=False)
        )

        collection = client.get_collection(
            name=self.config["PROJECT_NAME"], embedding_function=self.embedding_fn
        )

        collection_count = collection.count()
        print("collection ids count: ", collection_count)
        return

    def create_embeddings(self):
        if os.path.exists(self.persist_directory):
            shutil.rmtree(self.persist_directory)
        self.client = chromadb.PersistentClient(
            path=self.persist_directory, settings=Settings(anonymized_telemetry=False)
        )

        try:
            self.client.delete_collection(
                name=self.config["PROJECT_NAME"],
            )
        except:
            print("Creating new collection.")

        self.collection = self.client.create_collection(
            name=self.config["PROJECT_NAME"],
            embedding_function=self.embedding_fn,
        )
        self.documents = DirectoryLoader(
            os.path.join(
                os.path.join(os.environ["APP_PATH"], os.environ["DATA_PATH"]),
                "raw_documents",
            ),
            glob=self.config["GLOB_SUFFIX"],
        ).load()
        self.texts = []
        self.sources = []
        for document in self.documents:
            next_text = RecursiveCharacterTextSplitter(chunk_size=1000).split_text(
                document.page_content
            )  # list of chunks
            self.texts.extend(next_text)
            
            self.sources.extend(
                [
                    document.metadata["source"].split("/")[-1][:-4]
                    for _ in range(len(next_text))
                ]
            )

        self.texts = [text.replace("\n\n", "\n") for text in self.texts]
        self.collection.add(
            ids=[str(index) for index in range(len(self.texts))],
            metadatas=[{"source": source} for source in self.sources],
            documents=self.texts,
        )

        collection_count = self.collection.count()
        print("collection ids count: ", collection_count)
        return
