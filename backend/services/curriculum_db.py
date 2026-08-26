import os
import json
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB_NAME", "sih134")


def get_client():
    return MongoClient(MONGO_URI)


def get_db():
    return get_client()[DB_NAME]


def seed_curricula():
    from curriculum_db import INDIAN_CURRICULA as INDIAN_CURRICULUM

    client = get_client()
    db = client[DB_NAME]
    collection = db["curricula"]

    collection.create_index("name", unique=True)
    collection.create_index("type")

    inserted = 0
    updated = 0
    for name, data in INDIAN_CURRICULUM.items():
        result = collection.update_one(
            {"name": name},
            {"$set": {
                "name": name,
                "type": data["type"],
                "university": data["university"],
                "semesters": data["semesters"],
                "skills_by_semester": data.get("skills", {}),
                "all_skills": data["core_skills_taught"],
            }},
            upsert=True
        )
        if result.upserted_id:
            inserted += 1
        else:
            updated += 1

    print(f"Curricula: {inserted} inserted, {updated} updated in MongoDB")
    client.close()
    return inserted + updated


def get_all_curricula_from_db():
    client = get_client()
    db = client[DB_NAME]
    curricula = list(db["curricula"].find({}, {"_id": 0}))
    client.close()
    return curricula


def get_curriculum_from_db(name):
    client = get_client()
    db = client[DB_NAME]
    curriculum = db["curricula"].find_one({"name": name}, {"_id": 0})
    client.close()
    return curriculum


def update_curriculum_in_db(name, updates):
    client = get_client()
    db = client[DB_NAME]
    result = db["curricula"].update_one(
        {"name": name},
        {"$set": updates},
        upsert=True
    )
    client.close()
    return result.modified_count > 0 or result.upserted_id is not None


def delete_curriculum_from_db(name):
    client = get_client()
    db = client[DB_NAME]
    result = db["curricula"].delete_one({"name": name})
    client.close()
    return result.deleted_count > 0


if __name__ == "__main__":
    seed_curricula()
    curricula = get_all_curricula_from_db()
    print(f"\nTotal curricula in MongoDB: {len(curricula)}")
    for c in curricula:
        print(f"  - {c['name']} ({c['type']}, {len(c['all_skills'])} skills)")
