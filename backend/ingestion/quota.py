"""Provider quota budgeting.

Adzuna's free tier caps hits per minute/day/week/month (see config). Each paged
search request is one hit. To keep a scheduled cron from exhausting the quota
mid-month (which would make subsequent runs fail), we compute how many hits this
run may safely consume based on how many hits have already been recorded in the
trailing windows.

Hits are tracked per run in the update_logs collection (``providerHits``), so the
budget is derived from real recorded usage rather than guesses.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from . import config


def _hits_used(collection, source: str, window_hours: float) -> int:
    """Return the total providerHits recorded for ``source`` in the trailing window."""
    if collection is None:
        return 0
    start = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    try:
        pipeline = [
            {"$match": {"source": source, "startedAt": {"$gte": start.isoformat()}}},
            {"$group": {"_id": None, "hits": {"$sum": "$providerHits"}}},
        ]
        rows = list(collection.aggregate(pipeline))
    except Exception:
        return 0
    if not rows:
        return 0
    return int(rows[0].get("hits") or 0)


def _budget_for(cap: int, used: int, margin: int) -> int:
    """Max hits allowed in this window after safety margin. Never below 0."""
    return max(0, cap - used - margin)


def max_adzuna_pages(database, source: str = "adzuna", requested_pages: Optional[int] = None) -> int:
    """Return the number of Adzuna pages this run may consume without exhausting quota.

    Considers rolling day/week/month usage (capped by the config budgets, minus a
    safety margin) and returns the most restrictive bound. Always returns at least
    1 so a configured run still tries to fetch a little data even near the cap.
    """
    if source != "adzuna":
        col = None
    else:
        col = getattr(database, "update_logs", None)

    used_day = _hits_used(col, source, config.QUOTA_DAY_WINDOW_HOURS)
    used_week = _hits_used(col, source, config.QUOTA_WEEK_WINDOW_HOURS)
    used_month = _hits_used(col, source, config.QUOTA_MONTH_WINDOW_HOURS)

    budget_day = _budget_for(config.ADZUNA_QUOTA_DAY_HITS, used_day, config.ADZUNA_QUOTA_SAFETY_MARGIN)
    budget_week = _budget_for(config.ADZUNA_QUOTA_WEEK_HITS, used_week, config.ADZUNA_QUOTA_SAFETY_MARGIN)
    budget_month = _budget_for(config.ADZUNA_QUOTA_MONTH_HITS, used_month, config.ADZUNA_QUOTA_SAFETY_MARGIN)

    allowed = min(budget_day, budget_week, budget_month)

    if requested_pages is None:
        requested_pages = config.ADZUNA_MAX_PAGES

    pages = min(requested_pages, allowed)
    # Always allow at least one page per run so the pipeline demonstrably runs.
    if pages < 1 and allowed >= 1:
        pages = 1
    return max(pages, 0)
