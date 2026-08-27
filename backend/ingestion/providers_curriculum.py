"""Online curriculum skills source (NPTEL / SWAYAM / AICTE-aligned).

There is no clean public JSON API from SWAYAM/NPTEL that maps national MOOC
offerings back to a university curriculum's taught skills, and scraping their
HTML/spreadsheets inside a cron job is fragile and can silently fail a monthly
run.

This provider therefore uses a stable, curated mapping of emerging skills that
AICTE/NPTEL/SWAYAM actively promote. Each month the job merges these into the
matching curriculum's ``all_skills`` so the app's skill-gap analysis stays
current with national education-program trends.

An optional ``CURRICULUM_ONLINE_URL`` environment variable can point the job at
a future JSON/SV recuperable source; when set and reachable it is preferred and
the curated map is a fallback. On any failure the job returns nothing so the
caller never wipes existing data.
"""

import os
import json
from datetime import datetime, timezone

import requests

from . import config

# Emerging-skill themes aligned with NPTEL/SWAYAM/AICTE national programmes.
# Keyed by a substring matched case-insensitively against the curriculum name,
# so the same mapping works across B.E./B.Tech/BCA/MCA/etc. of a given branch.
CURRICULUM_SKILL_THEMES = {
    "computer": {
        "generative ai", "llm", "machine learning", "deep learning",
        "data structures", "algorithms", "operating systems", "sql",
        "python", "cloud computing", "cyber security", "docker",
    },
    "data": {
        "python", "sql", "pandas", "machine learning", "data science",
        "statistics", "big data", "cloud computing",
    },
    "information technology": {
        "python", "java", "sql", "web development", "cloud computing",
        "networking", "cyber security", "data structures", "algorithms",
    },
    "electronics": {
        "digital logic", "microprocessor", "embedded systems", "iot",
        "signals and systems", "python",
    },
}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _theme_for_curriculum(name: str) -> set:
    lower = name.lower()
    for key, skills in CURRICULUM_SKILL_THEMES.items():
        if key in lower:
            return skills
    return set(CURRICULUM_SKILL_THEMES.get("computer", set()))


def _fetch_from_url():
    """Optional online JSON source. Returns a dict {name: {patch fields}} or None."""
    url = os.getenv("CURRICULUM_ONLINE_URL", "").strip()
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def fetch_online_curriculum_updates():
    """Return {curriculum_name: {field: value}} patches for the monthly run.

    Tries the optional ``CURRICULUM_ONLINE_URL`` first; falls back to the
    curated AICTE/NPTEL-aligned skill themes. Returns {} on total failure so
    the caller leaves existing data untouched.
    """
    remote = _fetch_from_url()
    if remote:
        return remote

    # Build a mapping of every curriculum we know about to its theme skills.
    try:
        from services.curriculum_db_seed import INDIAN_CURRICULA
    except Exception:
        INDIAN_CURRICULA = {}

    from services.skills_taxonomy import normalize_skill_list

    updates = {}
    for name in INDIAN_CURRICULA:
        theme = _theme_for_curriculum(name)
        updates[name] = {
            "online_skills": normalize_skill_list(sorted(theme)),
            "onlineProvider": "nptel_swayam_aicte",
            "onlineCheckedAt": _now_iso(),
        }
    return updates
