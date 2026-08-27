"""Central configuration for the data ingestion system.

All secrets/API keys are read from environment variables (never hardcoded).
Provider quota/limit configuration is kept here so it is easy to tune without
touching ingestion logic.
"""

import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent.parent / "backend" / ".env")

# ---------------------------------------------------------------------------
# Job provider (Adzuna) credentials
# ---------------------------------------------------------------------------
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "").strip()
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "").strip()
ADZUNA_COUNTRY = os.getenv("ADZUNA_COUNTRY", "in").strip()
ADZUNA_BASE_URL = os.getenv("ADZUNA_BASE_URL", "https://api.adzuna.com/v1/api/jobs").strip()

# Number of pages to fetch per run and results per page.
ADZUNA_MAX_PAGES = int(os.getenv("ADZUNA_MAX_PAGES", "10"))
ADZUNA_RESULTS_PER_PAGE = int(os.getenv("ADZUNA_RESULTS_PER_PAGE", "50"))
# Minimum seconds to wait between provider requests to respect rate limits.
ADZUNA_REQUEST_DELAY = float(os.getenv("ADZUNA_REQUEST_DELAY", "1.0"))

# Allow the ingestion to run against generated/mock data when no valid API key
# is configured. This keeps the system useful for development and demos and
# never breaks when an external source is unavailable.
ENABLE_MOCK_FALLBACK = os.getenv("ENABLE_MOCK_FALLBACK", "true").lower() in ("1", "true", "yes")

# ---------------------------------------------------------------------------
# Scheduler / freshness configuration
# ---------------------------------------------------------------------------
JOBS_UPDATE_INTERVAL_HOURS = int(os.getenv("JOBS_UPDATE_INTERVAL_HOURS", "6"))
CURRICULUM_UPDATE_INTERVAL_DAYS = int(os.getenv("CURRICULUM_UPDATE_INTERVAL_DAYS", "30"))

# A job posting not seen again for this many days is marked inactive/expired
# rather than deleted.
STALE_JOB_DAYS = int(os.getenv("STALE_JOB_DAYS", "30"))

# ---------------------------------------------------------------------------
# Mock / fallback data generation (only used when no external API is configured)
# ---------------------------------------------------------------------------
MOCK_JOB_COUNT = int(os.getenv("MOCK_JOB_COUNT", "200"))
MOCK_JOB_SOURCE = "mock"

# Developer-facing function used by ingestion scripts and tests.
def adzuna_configured() -> bool:
    return bool(ADZUNA_APP_ID and ADZUNA_APP_KEY)
