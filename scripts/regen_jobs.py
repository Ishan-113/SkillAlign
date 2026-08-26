import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / "backend" / ".env")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scraper import generate_realistic_jobs

from pymongo import MongoClient

client = MongoClient(os.getenv("MONGO_URI"))
db = client["sih134"]

jobs = generate_realistic_jobs(200)
db.jobs.drop()
result = db.jobs.insert_many(jobs)
print(f"Inserted {len(result.inserted_ids)} jobs")

empty = db.jobs.count_documents({"skills": ""})
print(f"Jobs with empty skills: {empty}")
print(f"Total jobs: {db.jobs.count_documents({})}")
