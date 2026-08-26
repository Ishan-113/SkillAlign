import os
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path(__file__).resolve().parent.parent / "backend" / ".env")
client = MongoClient(os.getenv("MONGO_URI"))
db = client["sih134"]

fixed = 0
for job in db.jobs.find():
    skills = job["skills"]
    parts = [s.strip() for s in skills.split(",") if s.strip()]
    new_skills = ", ".join(parts)
    if new_skills != skills:
        db.jobs.update_one({"_id": job["_id"]}, {"$set": {"skills": new_skills}})
        fixed += 1

print(f"Fixed {fixed} jobs")
print(f"Total jobs: {db.jobs.count_documents({})}")
