"""Standalone scheduler entrypoint for Render Cron Jobs.

This script performs a MongoDB ingestion pass directly (no web app needed) on an
external schedule (e.g. Render Cron Job every 6 hours). It:

  * Connects to MongoDB Atlas using MONGO_URI / MONGO_DB_NAME env vars.
  * If ADZUNA_APP_ID / ADZUNA_APP_KEY are set, fetches live jobs (quota-aware)
    and upserts them into the `jobs` collection (dedup by source+externalId).
  * Otherwise falls back to the mock provider (dev/demo), so the run never breaks.
  * Marks stale jobs inactive (does not delete) and records everything in
    `update_logs`, exactly like the GitHub Actions entry point.

The fetched data is written straight to MongoDB -> the live API/frontend read it
from there unchanged. The scheduler itself stores nothing.

Run (from repo root):
    python scripts/render_cron_job.py jobs      # refresh jobs
    python scripts/render_cron_job.py curriculum # refresh curricula (monthly)

Exit code 0 on success, non-zero on hard failure (so the cron surfaces errors).
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv

load_dotenv(ROOT / "backend" / ".env")

import sys as _sys
from services.mongodb import get_ingestion_collections, build_indexes
from ingestion.job_ingestion import run_job_update
from ingestion.curriculum_ingestion import check_curriculum_updates


def _summary(result) -> str:
    d = result.to_dict()
    return (
        f"fetched={d['fetched']} inserted={d['inserted']} updated={d['updated']} "
        f"skipped={d['skipped']} failed={d['failed']} expired={d['expired']} "
        f"rate_limited={d['rate_limited']} error={d['error']}"
    )


def run_jobs():
    database = get_ingestion_collections()
    try:
        build_indexes(database)
        result = run_job_update(database)
        print(f"JOBS_UPDATE {_summary(result)}")
        return 0 if result.failed == 0 and not result.error else 1
    finally:
        client = getattr(database, "_sih_client", None)
        if client:
            client.close()


def run_curriculum():
    database = get_ingestion_collections()
    try:
        build_indexes(database)
        result = check_curriculum_updates(database)
        print(f"CURRICULUM_UPDATE {result}")
        return 0
    finally:
        client = getattr(database, "_sih_client", None)
        if client:
            client.close()


def main():
    kind = (sys.argv[1] if len(sys.argv) > 1 else "jobs").lower()
    if kind in ("curriculum", "curricula"):
        code = run_curriculum()
    elif kind in ("jobs", "job"):
        code = run_jobs()
    else:
        print(f"Unknown job type: {kind!r} (expected 'jobs' or 'curriculum')")
        return 2
    sys.exit(code)


if __name__ == "__main__":
    main()
