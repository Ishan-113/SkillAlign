"""Job ingestion service.

Responsibilities:
  * Fetch jobs from configured providers.
  * Map them to the application's existing document schema (plus provenance).
  * De-duplicate and update via unique (source, externalId) index.
  * Mark stale jobs as inactive instead of deleting them.
  * Record every attempt in update_logs.
"""

from datetime import datetime, timedelta, timezone

from . import config
from .providers import JobProvider, ProviderError, default_providers
from .mapper import to_app_job


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _millis(dt):
    return int(dt.timestamp() * 1000)


class IngestionResult:
    def __init__(self):
        self.fetched = 0
        self.inserted = 0
        self.updated = 0
        self.skipped = 0
        self.failed = 0
        self.expired = 0
        self.provider = None
        self.error = None

    def to_dict(self):
        return {
            "fetched": self.fetched,
            "inserted": self.inserted,
            "updated": self.updated,
            "skipped": self.skipped,
            "failed": self.failed,
            "expired": self.expired,
            "provider": self.provider,
            "error": self.error,
        }


def run_job_update(database, providers=None):
    """Run one jobs ingestion pass against ``database`` (a pymongo db handle).

    Returns an IngestionResult. On complete provider failure, existing data is
    left untouched and the failure is recorded in update_logs.
    """
    started = _now_iso()
    start_ms = _millis(datetime.now(timezone.utc))
    result = IngestionResult()
    used_collection = database["jobs"]

    providers = providers if providers is not None else default_providers()

    write_errors = []
    last_error = None

    for provider in providers:
        if not provider.is_configured():
            continue
        result.provider = provider.name
        try:
            jobs = provider.fetch_jobs()
        except ProviderError as e:
            last_error = str(e)
            result.failed += 1
            _write_log(database, provider.name, "jobs", started, start_ms, result, status="failed", error=last_error)
            continue

        result.fetched += len(jobs)
        seen_external = set()

        for job in jobs:
            external_id = str(job.get("externalId") or "")
            if external_id in seen_external:
                result.skipped += 1
                continue
            seen_external.add(external_id)

            try:
                app_job = to_app_job(job, db=database, source=provider.name)
            except Exception as e:  # data mapping errors should not kill a run
                result.failed += 1
                write_errors.append(str(e))
                continue

            if not external_id:
                result.failed += 1
                continue

            try:
                outcome = _upsert_job(used_collection, app_job, source=provider.name)
            except Exception as e:
                result.failed += 1
                write_errors.append(str(e))
                continue

            if outcome == "inserted":
                result.inserted += 1
            elif outcome == "updated":
                result.updated += 1
            else:
                result.skipped += 1

        # Mark unseen jobs as inactive (do not delete).
        result.expired += _expire_stale(used_collection, source=provider.name, seen=seen_external)
        break  # only run the first successfully-configured provider per pass

    # If a provider failed but another succeeded, log success with notes.
    if result.fetched > 0 and not last_error:
        status = "success"
    elif result.fetched == 0:
        status = "failed" if last_error else "no_data"
    else:
        status = "partial"

    _write_log(
        database,
        result.provider or "unknown",
        "jobs",
        started,
        start_ms,
        result,
        status=status,
        error=last_error or ("; ".join(write_errors[:3]) if write_errors else None),
    )
    return result


def _upsert_job(collection, app_job, source):
    """Insert or update one job based on (source, externalId).

    Returns 'inserted', 'updated', or 'skipped'.
    """
    query = {"source": source, "externalId": app_job["externalId"]}
    existing = collection.find_one(query, {"_id": 1})
    if existing is None:
        try:
            collection.insert_one(app_job)
            return "inserted"
        except Exception as e:
            if "duplicate" in str(e).lower() or e.code == 11000:
                # Race: another run inserted it. Update instead.
                pass
            else:
                raise
    # Update changed fields, always refreshing lastSeenAt/lastUpdatedAt.
    update_fields = dict(app_job)
    update_fields.pop("source", None)
    update_fields.pop("externalId", None)
    update_fields.pop("_id", None)
    collection.update_one(query, {"$set": update_fields})
    return "updated"


def _expire_stale(collection, source, seen):
    """Mark jobs from this source not seen in this run as inactive."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=config.STALE_JOB_DAYS)
    query = {
        "source": source,
        "status": "active",
        "lastSeenAt": {"$lt": cutoff.isoformat()},
    }
    res = collection.update_many(query, {"$set": {"status": "inactive", "lastUpdatedAt": _now_iso()}})
    return res.modified_count


def _write_log(database, source, data_type, started, start_ms, result, status, error):
    completed = _now_iso()
    end_ms = _millis(datetime.now(timezone.utc))
    log = {
        "source": source,
        "dataType": data_type,
        "startedAt": started,
        "completedAt": completed,
        "startedAtMs": start_ms,
        "completedAtMs": end_ms,
        "durationMs": end_ms - start_ms,
        "recordsFetched": result.fetched,
        "recordsInserted": result.inserted,
        "recordsUpdated": result.updated,
        "recordsSkipped": result.skipped,
        "recordsFailed": result.failed,
        "recordsExpired": result.expired,
        "status": status,
        "error": error,
    }
    try:
        database["update_logs"].insert_one(log)
    except Exception:
        pass
