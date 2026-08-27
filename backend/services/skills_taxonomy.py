"""Skill normalization and taxonomy.

Normalizes raw skill strings from job ads and university curricula to canonical
canonical names so both sides can be compared. The canonical mapping lives in
MongoDB (``skills`` collection) but a built-in fallback dictionary is provided so
ingestion still works even if the database is unreachable.
"""

import re
from typing import Dict, List, Optional, Tuple

# Built-in fallback taxonomy (canonical -> variants). The MongoDB ``skills``
# collection is authoritative when available; this is only used as a fallback so
# ingestion never depends on the network/database being reachable.
FALLBACK_TAXONOMY: Dict[str, Dict[str, List[str]]] = {
    "React": {
        "category": "Framework",
        "aliases": ["ReactJS", "React.js", "React JS", "React Native"],
    },
    "SQL": {
        "category": "Database",
        "aliases": ["MySQL", "SQL Database", "PL/SQL", "T-SQL", "Structured Query Language"],
    },
    "JavaScript": {
        "category": "Programming Language",
        "aliases": ["JS", "ECMAScript", "Vanilla JS"],
    },
    "TypeScript": {"category": "Programming Language", "aliases": ["TS"]},
    "Node.js": {"category": "Framework", "aliases": ["NodeJS", "Node JS", "Node"]},
    "Python": {"category": "Programming Language", "aliases": []},
    "Java": {"category": "Programming Language", "aliases": ["Core Java", "Java SE"]},
    "C#": {"category": "Programming Language", "aliases": ["CSharp", "C Sharp"]},
    "C++": {"category": "Programming Language", "aliases": ["CPP"]},
    "HTML": {"category": "Programming Language", "aliases": ["HTML5", "HyperText Markup Language"]},
    "CSS": {"category": "Programming Language", "aliases": ["CSS3", "Cascading Style Sheets"]},
    "AWS": {"category": "Cloud", "aliases": ["Amazon Web Services"]},
    "Azure": {"category": "Cloud", "aliases": ["Microsoft Azure"]},
    "Google Cloud": {"category": "Cloud", "aliases": ["GCP", "Google Cloud Platform"]},
    "Docker": {"category": "Tool", "aliases": []},
    "Kubernetes": {"category": "Tool", "aliases": ["K8s", "K8S"]},
    "Terraform": {"category": "Tool", "aliases": []},
    "Git": {"category": "Tool", "aliases": ["GIT", "Version Control(Git)"]},
    "GitHub": {"category": "Tool", "aliases": []},
    "GitLab": {"category": "Tool", "aliases": []},
    "Jenkins": {"category": "Tool", "aliases": []},
    "MongoDB": {"category": "Database", "aliases": ["Mongo", "Mongo DB"]},
    "PostgreSQL": {"category": "Database", "aliases": ["Postgres", "Postgresql"]},
    "Redis": {"category": "Database", "aliases": []},
    "Kafka": {"category": "Database", "aliases": []},
    "Spark": {"category": "Database", "aliases": ["Apache Spark"]},
    "Hadoop": {"category": "Database", "aliases": ["Apache Hadoop"]},
    "Machine Learning": {"category": "Technical Skill", "aliases": ["ML"]},
    "Deep Learning": {"category": "Technical Skill", "aliases": ["DL", "Neural Networks"]},
    "Artificial Intelligence": {"category": "Technical Skill", "aliases": ["AI"]},
    "TensorFlow": {"category": "Framework", "aliases": ["Tf", "Tensor flow"]},
    "PyTorch": {"category": "Framework", "aliases": []},
    "Django": {"category": "Framework", "aliases": []},
    "Flask": {"category": "Framework", "aliases": []},
    "FastAPI": {"category": "Framework", "aliases": []},
    "Spring Boot": {"category": "Framework", "aliases": ["Spring", "Springboot"]},
    "Angular": {"category": "Framework", "aliases": ["AngularJS", "Angular 2+"]},
    "Vue.js": {"category": "Framework", "aliases": ["Vue", "VueJS"]},
    "Next.js": {"category": "Framework", "aliases": ["NextJS", "Next JS"]},
    "Flutter": {"category": "Framework", "aliases": []},
    "Excel": {"category": "Tool", "aliases": ["Microsoft Excel", "MS Excel"]},
    "Communication": {"category": "Soft Skill", "aliases": ["Communication Skills", "Oral Communication"]},
    "Teamwork": {"category": "Soft Skill", "aliases": ["Team Work", "Collaboration"]},
    "Leadership": {"category": "Soft Skill", "aliases": []},
    "Problem Solving": {"category": "Soft Skill", "aliases": ["Problem-solving", "Problem Solving Skills"]},
    "Agile": {"category": "Soft Skill", "aliases": ["Agile Methodology", "Agile/Scrum"]},
    "Scrum": {"category": "Soft Skill", "aliases": []},
}

# Canonical neutral forms for skills that should be compared case-insensitively
# and ignoring common punctuation/spacing.
_CANONICAL_LOOKUP = {}


def _build_lookup() -> Dict[str, str]:
    if _CANONICAL_LOOKUP:
        return _CANONICAL_LOOKUP
    for canonical, entry in FALLBACK_TAXONOMY.items():
        key = _normalize_key(canonical)
        _CANONICAL_LOOKUP[key] = canonical
        for alias in entry.get("aliases", []):
            key = _normalize_key(alias)
            _CANONICAL_LOOKUP[key] = canonical
    return _CANONICAL_LOOKUP


def _normalize_key(value: str) -> str:
    value = value.strip().lower()
    # Remove common punctuation so "React JS" == "reactjs" == "React.js"
    value = re.sub(r"[.\-+/&()]", "", value)
    value = re.sub(r"\s+", "", value)
    return value


def normalize_skill(raw: str, db=None) -> Tuple[str, bool]:
    """Return (canonical_skill, was_normalized).

    ``db`` is an optional MongoDB database used to consult the ``skills``
    taxonomy collection (authoritative). If the raw value maps to no known
    canonical skill, the cleaned raw value is returned unchanged as its own
    canonical form.
    """
    if raw is None:
        return "", False
    value = raw.strip()
    if not value:
        return "", False

    if db is not None:
        try:
            found = db.skills.find_one({"aliases": value}, {"canonicalSkill": 1})
            if found and found.get("canonicalSkill"):
                return found["canonicalSkill"], True
        except Exception:
            pass

    key = _normalize_key(value)
    lookup = _build_lookup()
    if key in lookup:
        return lookup[key], True
    # Fall back to cleaned original value as its own canonical form.
    return value, False


def normalize_skill_list(raw_skills, db=None) -> list:
    """Normalize a list of raw skill strings to a de-duplicated canonical list."""
    normalized = {}
    for raw in raw_skills:
        canonical, _ = normalize_skill(raw, db=db)
        if canonical:
            normalized[canonical] = True
    return sorted(normalized.keys())
