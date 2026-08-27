"""Shared access to the curated Indian university curricula dataset.

The authoritative dataset lives in ``scripts/curriculum_db.py`` (INDIAN_CURRICULA)
and is also used by the manual ``scripts/seed_curricula.py`` seeder. This module
re-exports it so the scheduled ingestion service can import it from the backend
package without duplicating ~1200 lines of data.
"""

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from curriculum_db import INDIAN_CURRICULA  # noqa: E402

__all__ = ["INDIAN_CURRICULA"]
