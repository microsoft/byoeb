import asyncio
import json
import os
import pytest
from byoeb_integrations.databases.mongo_db.azure.async_azure_cosmos_mongo_db import AsyncAzureCosmosMongoDB, AsyncAzureCosmosMongoDBCollection
from byoeb_integrations import test_environment_path
from dotenv import load_dotenv

load_dotenv(test_environment_path)
connection_string = os.getenv("MONGO_DB_CONNECTION_STRING")
db_name = "test_new_frame"

c1 = "c1"
c2 = "c2"

@pytest.fixture(scope="session")
def event_loop():
    """Create and reuse a single event loop for all tests in the session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop

async def aazure_cosmos_mongo_db_batch():
    db_client = AsyncAzureCosmosMongoDB(connection_string, db_name)
    documents = [
        {"_id": "101", "name": "Alice", "email": "alice@example.com", "age": 25},
        {"_id": "102", "name": "Bob", "email": "bob@example.com", "age": 30},
        {"_id": "103", "name": "Charlie", "email": "charlie@example.com", "age": 35}
    ]
    await db_client.adelete_collection(c1)
    collection1 = db_client.get_collection(c1)
    c1_client = AsyncAzureCosmosMongoDBCollection(collection1)
    results = await c1_client.ainsert(documents)
    data = await c1_client.afetch_all({"age": {"$gte": 26}})
    c1_client.aupdate({"age": 25}, {"$set": {"age": 26}})
    ids = await c1_client.afetch_ids()
    assert len(ids) == len(documents)
    data_id = await c1_client.afetch({"_id": "102"})
    assert data_id is not None
    assert data_id["name"] == "Bob"
    await c1_client.adelete_collection()
    await db_client.adelete_database()

async def aazure_cosmos_mongo_db():
    db_client = AsyncAzureCosmosMongoDB(connection_string, db_name)
    test_data = {
        "name": "John",
        "age": 30,
        "city": "New York"
    }
    await db_client.adelete_collection(c1)
    await db_client.adelete_collection(c2)
    collection1 = db_client.get_collection(c1)
    collection2 = db_client.get_collection(c2)
    c1_client = AsyncAzureCosmosMongoDBCollection(collection1)
    c2_client = AsyncAzureCosmosMongoDBCollection(collection2)
    await c1_client.ainsert([test_data])
    data = await c1_client.afetch_all({"name": "John"})
    assert data is not None
    assert data[0]["name"] == "John"
    update_data = {"$set":{"name": "Jane"}}
    result, modified = await c1_client.aupdate(bulk_queries=[({"name": "John"}, update_data)])
    print(modified)
    data = await c1_client.afetch_all({"name": "Jane"})
    result, delete_count = await c1_client.adelete(bulk_queries=[{"name": "Jane"}])
    print(delete_count)
    assert data is not None
    assert data[0]["name"] == "Jane"
    data = await c2_client.afetch_all({"name": "Jane"})
    assert len(data) == 0
    await c1_client.adelete_collection()
    await c2_client.adelete_collection()
    await db_client.adelete_database()

async def aazure_byoeb_delete():
    db_name = "byoebv1"
    db_client = AsyncAzureCosmosMongoDB(connection_string, db_name)
    await db_client.adelete_database()

async def inspect():
    db_name = "byoebv1"
    db_client = AsyncAzureCosmosMongoDB(connection_string, db_name)
    collection1 = db_client.get_collection("byoebmessages")
    c1_client = AsyncAzureCosmosMongoDBCollection(collection1)
    results = await c1_client.afetch_all()
    for result in results:
        print(json.dumps(result))
    await c1_client.adelete_collection()

# asyncio.run(aazure_cosmos_mongo_db())
def test_aazure_cosmos_mongo_db_batch(event_loop):
    event_loop.run_until_complete(aazure_cosmos_mongo_db_batch())

def test_aazure_cosmos_mongo_db(event_loop):
    event_loop.run_until_complete(aazure_cosmos_mongo_db())

if __name__ == "__main__":
    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(inspect())
    event_loop.close()