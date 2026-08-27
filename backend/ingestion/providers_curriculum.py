"""Online curriculum skills source (real JSON).

The monthly ingestion fetches a machine-readable JSON dataset from
``CURRICULUM_ONLINE_URL`` (or the committed ``curriculum_source/`` file when the
URL is empty). Each entry is keyed by the curriculum ``name`` and carries the
fields the application's skill-gap analysis reads (notably ``all_skills``), so
the job can merge genuinely refreshed data into ``curricula``.

Two ways to supply the source, in priority order:
  1. ``CURRICULUM_ONLINE_URL`` - a hosted JSON endpoint (e.g. GitHub raw/Pages or a
     Render route). Preferred when set.
  2. The checked-out ``curriculum_source/curriculum_updates.json`` - used when the
     repo itself is the source of truth (e.g. the GitHub Actions runner).

Expected JSON shape (see ``scripts/build_curriculum_source.py``):
    {
      "source": "nptel_swayam_aicte",
      "version": 1,
      "generatedAt": "<ISO timestamp>",
      "curricula": {
        "<curriculum name>": {
          "type": "...",
          "university": "...",
          "semesters": 8,
          "all_skills": [...],
          "online_skills": [...]
        }
      }
    }

On any failure (unreachable, invalid shape, missing data) the job returns nothing,
so the caller never wipes existing curricula.
"""

import os
import json
from pathlib import Path
from datetime import datetime, timezone

import requests

# Union of every field the ingest layer is allowed to merge from the source.
# ``name`` is intentionally excluded because the URL entries are keyed by name.
ALLOWED_FIELDS = {
    "type", "university", "semesters", "all_skills",
    "skills_by_semester", "online_skills", "onlineProvider",
}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _repo_file_candidates():
    """Path(s) to the committed curriculum JSON relative to this repo."""
    here = Path(__file__).resolve()
    roots = [here.parents[2], here.parents[3]]  # backend/ingestion -> repo root
    for root in roots:
        candidate = root / "curriculum_source" / "curriculum_updates.json"
        if candidate.exists():
            return candidate
    return None


def _load_from_url(url):
    """Fetch and parse the hosted JSON source. Returns a dict on success."""
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def _load_from_file(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None


def _extract_updates(payload) -> dict:
    """Validate a payload and return {curriculum_name: {patch fields}}."""
    if not isinstance(payload, dict):
        return {}
    curricula = payload.get("curricula")
    if not isinstance(curricula, dict) or not curricula:
        return {}

    updates = {}
    for name, data in curricula.items():
        if not isinstance(data, dict):
            continue
        patch = {k: v for k, v in data.items() if k in ALLOWED_FIELDS}
        patch["onlineProvider"] = patch.get("onlineProvider") or payload.get("source") or "online"
        patch["onlineCheckedAt"] = _now_iso()
        updates[name] = patch
    return updates


def fetch_online_curriculum_updates():
    """Return {curriculum_name: {field: value}} patches merged from the JSON source.

    Tries ``CURRICULUM_ONLINE_URL`` first, then the committed repo file. Returns {}
    on any total failure so existing curricula are never lost.
    """
    url = os.getenv("CURRICULUM_ONLINE_URL", "").strip()
    payload = None
    used = None

    if url:
        payload = _load_from_url(url)
        used = "url"

    if not payload:
        repo_file = _repo_file_candidates()
        if repo_file:
            payload = _load_from_file(repo_file)
            used = "repo_file"

    if not payload:
        return {}

    updates = _extract_updates(payload)
    if not updates:
        return {}

    # Stamp provenance so the MongoDB docs record where the data came from.
    for patch in updates.values():
        patch.setdefault("source", payload.get("source") or "online")
        patch["onlineSource"] = used
    return updates
