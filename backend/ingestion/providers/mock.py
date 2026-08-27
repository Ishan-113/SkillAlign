"""Mock provider used as a graceful fallback when no live job API key is set.

It generates realistic-looking Indian job data so the application and the
scheduled pipeline remain fully functional without an external API. Whenever a
real provider is configured it should be preferred over this one.

Reuses the synthetic data generation already present in scripts/scraper.py so we
do not duplicate logic or change the shape of existing data.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List

from .base import JobProvider
from .. import config


class MockJobProvider(JobProvider):
    name = config.MOCK_JOB_SOURCE

    def is_configured(self) -> bool:
        # The mock provider is always "configured" but should only be used when
        # explicitly enabled (i.e. as the fallback) to avoid masking real data.
        return config.ENABLE_MOCK_FALLBACK

    def fetch_jobs(self) -> List[dict]:
        # Import lazily so a missing scraper module never breaks other providers.
        try:
            from scripts.scraper import generate_realistic_jobs
        except Exception:
            # Last-resort minimal generator
            from . import _fallback_factory
            jobs = _fallback_factory.generate_minimal_jobs(config.MOCK_JOB_COUNT)
        else:
            jobs = generate_realistic_jobs(config.MOCK_JOB_COUNT)

        normalized = []
        for job in jobs:
            posted = job.get("posting_date")
            if posted:
                try:
                    posted_at = datetime.strptime(posted, "%Y-%m-%d").isoformat()
                except (ValueError, TypeError):
                    posted_at = datetime.utcnow().isoformat()
            else:
                posted_at = datetime.utcnow().isoformat()

            normalized.append({
                "externalId": f"mock-{job.get('job_id', hash(str(job)) % 1000000)}",
                "title": job.get("title", ""),
                "company": job.get("company", ""),
                "location": job.get("location", ""),
                "description": "",
                "requirements": [s.strip() for s in str(job.get("skills", "")).split(",") if s.strip()],
                "salaryMin": None,
                "salaryMax": None,
                "salaryRaw": job.get("salary_range"),
                "category": job.get("domain"),
                "postedAt": posted_at,
            })
        return normalized
