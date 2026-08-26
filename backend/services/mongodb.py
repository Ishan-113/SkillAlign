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
