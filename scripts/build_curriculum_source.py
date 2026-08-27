"""Regenerate the hosted curriculum JSON source (curriculum_source/curriculum_updates.json).

This produces the machine-readable dataset the monthly ingestion fetches from
``CURRICULUM_ONLINE_URL``. It is built from the curated INDIAN_CURRICULA dataset
(real semester-wise subjects) plus the AICTE/NPTEL/SWAYAM aligned skill themes,
so the hosted JSON is real, current data rather than static example content.

Usage:
    python scripts/build_curriculum_source.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Emerging-skill themes aligned with NPTEL/SWAYAM/AICTE national programmes,
# used only to build the hosted JSON source (not read at ingest time).
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


def _theme_for_curriculum(name: str) -> set:
    lower = name.lower()
    for key, skills in CURRICULUM_SKILL_THEMES.items():
        if key in lower:
            return skills
    return set(CURRICULUM_SKILL_THEMES.get("computer", set()))


def build_source() -> dict:
    from services.curriculum_db_seed import INDIAN_CURRICULA
    from services.skills_taxonomy import normalize_skill_list

    curricula = {}
    for name, data in INDIAN_CURRICULA.items():
        core = list(data.get("core_skills_taught", []))
        theme = _theme_for_curriculum(name)
        online = normalize_skill_list(sorted(set(theme)))
        curricula[name] = {
            "type": data["type"],
            "university": data["university"],
            "semesters": data["semesters"],
            "all_skills": core,
            "online_skills": online,
            "onlineProvider": "nptel_swayam_aicte",
        }
    return {
        "version": 1,
        "source": "nptel_swayam_aicte",
        "generatedAt": None,  # replaced below with a fresh timestamp
        "curricula": curricula,
    }


def main():
    from datetime import datetime, timezone

    source = build_source()
    source["generatedAt"] = datetime.now(timezone.utc).isoformat()

    out = Path(__file__).resolve().parent.parent / "curriculum_source" / "curriculum_updates.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(source, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {out} with {len(source['curricula'])} curricula")


if __name__ == "__main__":
    main()
