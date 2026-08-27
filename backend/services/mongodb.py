import os
import traceback
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB_NAME", "sih134")

client = None
db = None


async def connect_db():
    global client, db
    try:
        client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        await db.command("ping")
        print(f"Connected to MongoDB: {DB_NAME}")
        return db
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        traceback.print_exc()
        db = None
        return None


def get_db():
    return db


async def close_db():
    global client
    if client:
        client.close()
        print("MongoDB connection closed")


async def insert_jobs(jobs):
    if not db:
        await connect_db()
    result = await db.jobs.insert_many(jobs, ordered=False)
    return len(result.inserted_ids)


async def insert_users(users):
    if not db:
        await connect_db()
    result = await db.users.insert_many(users, ordered=False)
    return len(result.inserted_ids)


async def get_jobs_collection():
    if not db:
        await connect_db()
    return db.jobs


async def get_users_collection():
    if not db:
        await connect_db()
    return db.users


async def get_analysis_collection():
    if not db:
        await connect_db()
    return db.analysis_sessions


def get_ingestion_collections():
    """Return a plain (blocking) database handle for the ingestion scripts.

    The scheduled ingestion runs outside the web request/async loop, so it uses
    pymongo's synchronous driver directly through this helper.
    """
    from pymongo import MongoClient

    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    database = client[DB_NAME]
    # Attach the client on the database object so the caller can close it.
    setattr(database, "_sih_client", client)
    return database


def build_indexes(database):
    """Create the indexes required by the ingestion system.

    A unique compound index on (source, externalId) prevents duplicate jobs,
    per the data-quality requirements.
    """
    jobs = database["jobs"]
    jobs.create_index([("source", 1), ("externalId", 1)], unique=True, sparse=True)
    jobs.create_index("location")
    jobs.create_index("postedAt")
    jobs.create_index("status")
    jobs.create_index("lastSeenAt")

    database["update_logs"].create_index([("source", 1), ("startedAt", -1)])
    database["update_logs"].create_index("dataType")

    # The collection the application's skill-gap analysis actually reads.
    database["curricula"].create_index("name", unique=True)
    database["curricula"].create_index("type")
