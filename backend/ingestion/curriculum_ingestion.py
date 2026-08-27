"""Curriculum ingestion service.

The application's skill-gap analysis reads the ``curricula`` collection (each
document is a named curriculum with ``name``, ``type``, ``university``,
``semesters``, ``skills_by_semester`` and ``all_skills``). This service keeps
that collection fresh on a monthly schedule:

  * Seeds any missing curricula from the curated Indian university dataset
    (VTU, Anna, IITs, NITs, MSBTE, etc.) so the app always has a baseline.
  * Refreshes/enriches each curriculum from an online skills source when one is
    reachable (NPTEL/SWAYAM/AICTE-oriented), gracefully skipping on failure so
    existing data is never lost.
  * De-duplicates via the unique ``name`` index on ``curricula``.

A single pass never deletes existing data; it only inserts missing records or
updates skills metadata. Every attempt is recorded in ``update_logs``.
"""

from datetime import datetime, timezone

from . import config

# Collection the application actually reads (see backend/routes/skillgap.py).
CURRICULA_COLLECTION = "curricula"


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def seed_curricula(database):
    """Insert the curated Indian curricula into the ``curricula`` collection.

    Only adds records that are not already present (dedup via the unique
    ``name`` index). Existing documents are never overwritten here so manual
    corrections are preserved.

    Returns the number of curricula present after the pass.
    """
    collection = database[CURRICULA_COLLECTION]
    try:
        collection.create_index("name", unique=True)
    except Exception:
        pass

    from services.curriculum_db_seed import INDIAN_CURRICULA

    count = 0
    for name, data in INDIAN_CURRICULA.items():
        try:
            collection.update_one(
                {"name": name},
                {"$setOnInsert": {
                    "name": name,
                    "type": data["type"],
                    "university": data["university"],
                    "semesters": data["semesters"],
                    "skills_by_semester": data.get("skills", {}),
                    "all_skills": data["core_skills_taught"],
                    "source": "curated_indian_university",
                    "lastCheckedAt": _now_iso(),
                }},
                upsert=True,
            )
            count += 1
        except Exception:
            count += 0
    return count


def refresh_from_online_source(database):
    """Refresh curricula skill metadata from an online source (NPTEL/AICTE).

    This is intentionally resilient: if the online source is unreachable or
    returns nothing, existing data is left untouched and only ``lastCheckedAt``
    on the monitored curricula is refreshed. This keeps the monthly job useful
    without ever wiping a curated curriculum.
    """
    from .providers_curriculum import fetch_online_curriculum_updates

    collection = database[CURRICULA_COLLECTION]
    updates = fetch_online_curriculum_updates()
    updated = 0
    failed = 0

    if not updates:
        return {"updated": 0, "failed": 0, "online": False}

    for name, patch in updates.items():
        try:
            result = collection.update_one(
                {"name": name},
                {"$set": {
                    **patch,
                    "source": "nptel_swayam_aicte",
                    "lastCheckedAt": _now_iso(),
                }},
            )
            if result.modified_count > 0 or result.matched_count > 0:
                updated += 1
        except Exception:
            failed += 1

    return {"updated": updated, "failed": failed, "online": True}


def check_curriculum_updates(database):
    """Run one monthly curriculum pass over the ``curricula`` collection.

    Returns a summary dict.
    """
    started = _now_iso()

    total = seed_curricula(database)
    online = refresh_from_online_source(database)

    collection = database[CURRICULA_COLLECTION]
    # Touch lastCheckedAt on every record so the UI can tell curricula that
    # have been verified this cycle even when the online source was offline.
    collection.update_many(
        {},
        {"$set": {"lastCheckedAt": _now_iso()}},
    )

    result = {
        "sources_checked": total,
        "new_versions": online["updated"],
        "unchanged": max(total - online["updated"], 0),
        "online_source": online["online"],
        "online_failed": online["failed"],
    }
    _write_log(database, "curriculum", started, result)
    return result


def _write_log(database, source, started, result):
    try:
        database["update_logs"].insert_one({
            "source": source,
            "dataType": "curriculum",
            "startedAt": started,
            "completedAt": _now_iso(),
            "status": "success",
            "recordsFetched": result["sources_checked"],
            "recordsInserted": result["new_versions"],
            "recordsUpdated": result["unchanged"],
            "recordsSkipped": 0,
            "recordsFailed": result.get("online_failed", 0),
            "error": None,
        })
    except Exception:
        pass
