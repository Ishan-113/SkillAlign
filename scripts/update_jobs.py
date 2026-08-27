"""Scheduled job ingestion entry point.

Run from GitHub Actions (or any scheduler) on an interval (default every 6h):

    python scripts/update_jobs.py

Reads credentials from environment variables (ADZUNA_APP_ID / ADZUNA_APP_KEY),
respects provider rate limits, de-duplicates by (source, externalId), expires
stale jobs, and writes an update_logs record. Never wipes existing data on
failure.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / "backend" / ".env")

from services.mongodb import get_ingestion_collections, build_indexes
from ingestion.job_ingestion import run_job_update


def main():
    database = get_ingestion_collections()
    build_indexes(database)
    result = run_job_update(database)
    client = getattr(database, "_sih_client", None)
    if client:
        client.close()

    print(json_summary(result))
    if result.error:
        print(f"NOTE: {result.error}")


def json_summary(result):
    d = result.to_dict()
    base = (
        f"Update complete [{d['provider'] or 'no-provider'}]: "
        f"fetched={d['fetched']}, inserted={d['inserted']}, "
        f"updated={d['updated']}, skipped={d['skipped']}, "
        f"failed={d['failed']}, expired={d['expired']}"
    )
    if d.get("rate_limited"):
        base += " [quota limited - stopped early]"
    return base


if __name__ == "__main__":
    main()
