"""Scheduled curriculum update entry point.

Run from GitHub Actions (or any scheduler) on an interval (default every
month):

    python scripts/update_curriculum.py

Maintains the university registry, refreshes curriculum_sources, and stores a
new versioned curricular record only when a new academic-year curriculum is
found (older versions are never overwritten).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / "backend" / ".env")

from services.mongodb import get_ingestion_collections, build_indexes
from ingestion.curriculum_ingestion import check_curriculum_updates


def main():
    database = get_ingestion_collections()
    build_indexes(database)
    result = check_curriculum_updates(database)
    client = getattr(database, "_sih_client", None)
    if client:
        client.close()

    print(
        f"Curriculum update complete: curricula_present={result['sources_checked']}, "
        f"refreshed={result['new_versions']}, unchanged={result['unchanged']}, "
        f"online_source={result['online_source']}"
    )


if __name__ == "__main__":
    main()
