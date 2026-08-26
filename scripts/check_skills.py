import os
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path(__file__).resolve().parent.parent / "backend" / ".env")
client = MongoClient(os.getenv("MONGO_URI"))
db = client["sih134"]

empty = db.jobs.count_documents({"skills": ""})
print(f"Jobs with empty skills: {empty}")

sample = db.jobs.find_one({"skills": ""})
if sample:
    print(f"Sample empty: {sample['title']} - skills: '{sample['skills']}'")

sample2 = db.jobs.find_one({"skills": {"$ne": ""}})
if sample2:
    print(f"Sample good: {sample2['title']} - skills: '{sample2['skills'][:80]}'")
