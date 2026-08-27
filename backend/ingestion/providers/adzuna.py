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


class AdzunaJobProvider(JobProvider):
    name = "adzuna"

    def __init__(self, app_id: str = None, app_key: str = None, country: str = None):
        self.app_id = app_id if app_id is not None else config.ADZUNA_APP_ID
        self.app_key = app_key if app_key is not None else config.ADZUNA_APP_KEY
        self.country = country if country is not None else config.ADZUNA_COUNTRY

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
        if resp.status_code == 429:
            raise ProviderError("rate limit hit (HTTP 429)", provider=self.name)
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

        jobs: List[dict] = []
        for page in range(1, config.ADZUNA_MAX_PAGES + 1):
            data = self._request(page)
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
