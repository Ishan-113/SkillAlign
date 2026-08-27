"""Adzuna Jobs API provider.

Documentation: https://developer.adzuna.com/
Endpoints used:
  GET /v1/api/jobs/{country}/search/{page}?app_id=..&app_key=..&results_per_page=..

Provides a legitimate, licensed source of job postings. Respects rate limits via
a configurable delay between requests and incremental paging. Never called
synchronously from the frontend; only the scheduled ingestion runs it.
"""

import time
from datetime import datetime, timezone
from typing import List

import requests

from .base import JobProvider, ProviderError
from .. import config


class RateLimitError(ProviderError):
    """Signals the provider's rate/quota limit was reached.

    The ingestion layer treats this as a graceful 'nothing more to fetch right
    now' condition: it keeps existing data, records a note, and does NOT fail
    the run so a quota-hit never breaks the scheduled cron.
    """

    def __init__(self, message: str = "provider rate/quota limit reached", provider: str = None):
        super().__init__(message or "provider rate/quota limit reached", provider=provider)


class AdzunaJobProvider(JobProvider):
    name = "adzuna"

    def __init__(self, app_id: str = None, app_key: str = None, country: str = None, max_pages: int = None):
        self.app_id = app_id if app_id is not None else config.ADZUNA_APP_ID
        self.app_key = app_key if app_key is not None else config.ADZUNA_APP_KEY
        self.country = country if country is not None else config.ADZUNA_COUNTRY
        # Cap pages for this run (quota-aware). Falls back to the config hard cap.
        self.max_pages = max_pages if max_pages is not None else config.ADZUNA_MAX_PAGES
        self.hits = 0  # number of HTTP requests (hits) actually made this run
        self.rate_limited = False  # True if we stopped early due to quota

    def is_configured(self) -> bool:
        return bool(self.app_id and self.app_key)

    def _request(self, page: int) -> dict:
        url = f"{config.ADZUNA_BASE_URL}/{self.country}/search/{page}"
        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "results_per_page": config.ADZUNA_RESULTS_PER_PAGE,
            "content-type": "application/json",
        }
        resp = requests.get(url, params=params, timeout=30)
        self.hits += 1
        # 429 is a quota/rate-limit signal: raise the non-fatal RateLimitError.
        if resp.status_code == 429:
            raise RateLimitError("Adzuna rate/quota limit hit (HTTP 429)", provider=self.name)
        if resp.status_code >= 500:
            raise ProviderError(f"server error (HTTP {resp.status_code})", provider=self.name)
        if resp.status_code >= 400:
            raise ProviderError(f"request rejected (HTTP {resp.status_code})", provider=self.name)
        try:
            return resp.json()
        except ValueError as e:
            raise ProviderError(f"invalid JSON response: {e}", provider=self.name) from e

    def fetch_jobs(self) -> List[dict]:
        if not self.is_configured():
            raise ProviderError("Adzuna app_id/app_key not configured", provider=self.name)
        if self.max_pages < 1:
            # Quota budget is exhausted for this run; do not make any request.
            self.rate_limited = True
            return []

        jobs: List[dict] = []
        for page in range(1, self.max_pages + 1):
            if self.hits >= self.max_pages:
                break
            try:
                data = self._request(page)
            except RateLimitError:
                self.rate_limited = True
                break  # keep whatever we already fetched; do not fail the run
            results = data.get("results", [])
            if not results:
                break
            for item in results:
                jobs.append(self._normalize(item))
            time.sleep(config.ADZUNA_REQUEST_DELAY)
            # stop when there are no more pages
            if page >= data.get("count", 0) / max(config.ADZUNA_RESULTS_PER_PAGE, 1):
                break
        return jobs

    def _normalize(self, item: dict) -> dict:
        salary_min = item.get("salary_min")
        salary_max = item.get("salary_max")
        # Adzuna returns negative salaries for "undisclosed"
        if isinstance(salary_min, (int, float)) and salary_min < 0:
            salary_min = None
        if isinstance(salary_max, (int, float)) and salary_max < 0:
            salary_max = None
        salary_raw = item.get("salary_is_predicted")
        if isinstance(salary_raw, str):
            salary_raw = item.get("salary_min", "") or ""
        elif salary_min is not None or salary_max is not None:
            salary_raw = f"{salary_min if salary_min is not None else ''}-{salary_max if salary_max is not None else ''}"
        else:
            salary_raw = ""

        location = item.get("location", {})
        location_label = location.get("display_name") or location.get("area") or item.get("location", "")

        # Adzuna provides a short description plus, sometimes, a "description"
        # HTML blob. Merge them for a usable requirements source.
        description = item.get("description", "")
        short_desc = item.get("short_description", "")
        full_desc = " ".join(x for x in [short_desc, description] if x)

        return {
            "externalId": str(item.get("id", "")),
            "title": item.get("title", ""),
            "company": (item.get("company") or {}).get("display_name") or "",
            "location": str(location_label or ""),
            "description": full_desc,
            "requirements": [],
            "salaryMin": salary_min,
            "salaryMax": salary_max,
            "salaryRaw": str(salary_raw or ""),
            "category": item.get("category", {}).get("label") if isinstance(item.get("category"), dict) else item.get("category"),
            "postedAt": item.get("created"),
        }
