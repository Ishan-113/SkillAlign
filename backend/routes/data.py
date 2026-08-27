"""Data freshness and ingestion metadata endpoints.

These endpoints report on the automatically collected data source: last
successful update times, active job counts, and registry/source information. They
read only from MongoDB (the cached data source) and never trigger external API
calls, so opening the dashboard never consumes provider quota.
"""

from datetime import datetime, timezone

from fastapi import APIRouter
from pymongo import MongoClient
from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB_NAME", "sih134")

router = APIRouter()

_CLIENT = None


def _db():
    global _CLIENT
    _CLIENT = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    return _CLIENT[DB_NAME]


def _close(db):
    global _CLIENT
    try:
        _CLIENT.close()
    except Exception:
        pass
    finally:
        _CLIENT = None


@router.get("/data/freshness")
async def get_data_freshness():
    db = _db()
    try:
        jobs_log = db["update_logs"].find(
            {"dataType": "jobs"}, {"_id": 0}
        ).sort("startedAtMs", -1).limit(1)

        curr_log = db["update_logs"].find(
            {"dataType": "curriculum"}, {"_id": 0}
        ).sort("startedAtMs", -1).limit(1)

        active_jobs = db["jobs"].count_documents(
            {"$or": [{"status": "active"}, {"status": {"$exists": False}}]}
        )
        total_jobs = db["jobs"].count_documents({})

        jobs_log = list(jobs_log)
        curr_log = list(curr_log)

        # count recently added/updated in the last 7 days
        from datetime import timedelta
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        recently = db["jobs"].count_documents({"postedAt": {"$gte": week_ago}})

        sources = sorted(db["jobs"].distinct("source"))

        return {
            "jobs": {
                "last_update": jobs_log[0].get("completedAt") if jobs_log else None,
                "last_update_status": jobs_log[0].get("status") if jobs_log else None,
                "last_update_error": jobs_log[0].get("error") if jobs_log else None,
                "active_jobs": active_jobs,
                "total_jobs": total_jobs,
                "added_recently_7d": recently,
                "sources": sources,
            },
            "curriculum": {
                "last_check": curr_log[0].get("completedAt") if curr_log else None,
                "last_update_status": curr_log[0].get("status") if curr_log else None,
            },
        }
    finally:
        _close(db)


@router.get("/data/universities")
async def list_universities():
    db = _db()
    try:
        unis = list(db["universities"].find({}, {"_id": 0}).sort("name", 1))
        return {"universities": unis, "total": len(unis)}
    finally:
        _close(db)


@router.get("/data/sources")
async def list_sources():
    db = _db()
    try:
        sources = list(db["curriculum_sources"].find({}, {"_id": 0}).sort("universityName", 1))
        return {"sources": sources, "total": len(sources)}
    finally:
        _close(db)


@router.get("/data/jobs")
async def list_jobs(limit: int = 50, offset: int = 0, active_only: bool = True):
    """Return raw jobs (legacy schema + provenance) for the dashboard.

    Legacy rows without a ``status`` field are treated as active so old data
    still appears until the ingestion system re-stamps them.
    """
    db = _db()
    try:
        if active_only:
            query = {"$or": [{"status": "active"}, {"status": {"$exists": False}}]}
        else:
            query = {}
        docs = list(
            db["jobs"].find(query, {"_id": 0}).sort("posting_date", -1).skip(offset).limit(limit)
        )
        total = db["jobs"].count_documents(query)
        return {"jobs": docs, "total": total}
    finally:
        _close(db)
