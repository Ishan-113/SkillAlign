"""Job provider registry.

Multiple providers can be registered and, on failure, ingestion may fall back
to the next configured provider.
"""

from typing import List

from .base import JobProvider, ProviderError
from .adzuna import AdzunaJobProvider
from .mock import MockJobProvider


def default_providers() -> List[JobProvider]:
    """Order matters: prefer the real provider, use mock only as fallback."""
    return [AdzunaJobProvider(), MockJobProvider()]


__all__ = ["JobProvider", "ProviderError", "AdzunaJobProvider", "MockJobProvider", "default_providers"]
