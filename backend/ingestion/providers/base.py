"""Base class for job data providers.

Each provider returns a normalized list of jobs in a provider-neutral shape.
The ingestion service is responsible for persisting them to MongoDB using the
application's existing document schema plus provenance metadata.
"""

from abc import ABC, abstractmethod
from typing import List, Optional


class JobProvider(ABC):
    """Abstract interface every job source must implement.

    The normalized job dict returned by ``fetch_jobs`` should contain:
        externalId   - provider-specific unique id (required for de-duplication)
        title        - job title
        company      - hiring company
        location     - human-readable location string
        description  - original job description text
        requirements - list of raw requirement strings (may be empty)
        salaryMin    - optional lower salary bound (number)
        salaryMax    - optional upper salary bound (number)
        salaryRaw    - optional human-readable salary string
        category     - optional job category
        postedAt     - optional ISO datetime of posting
    """

    name: str = "base"

    @abstractmethod
    def fetch_jobs(self) -> List[dict]:
        """Fetch a full snapshot of jobs from this provider.

        Implementations should be resilient: on failure they should raise a
        ProviderError (so the ingestion layer can log it and keep existing
        data), not silently return partial results.
        """
        raise NotImplementedError

    def is_configured(self) -> bool:
        """Return True if this provider can be used right now."""
        return True


class ProviderError(Exception):
    """Raised when a provider cannot be reached or returns invalid data.

    The ingestion layer catches this, records it in update_logs, and keeps the
    previously stored data intact.
    """

    def __init__(self, message: str = "", provider: Optional[str] = None):
        self.provider = provider
        full = (provider or "provider") + ": " + message if message else (provider or "provider")
        super().__init__(full)
