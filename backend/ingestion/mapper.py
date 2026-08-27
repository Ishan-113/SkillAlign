"""Helpers to map provider-neutral jobs to the application's existing document
schema so the existing API routes and frontend keep working unchanged.

Also extracts derived fields (experience_years, salary_range) that the legacy
schema requires but live providers may not provide directly.
"""

import re
from datetime import datetime
from typing import Optional

from services.skills_taxonomy import normalize_skill_list


def parse_experience_years(title: str, description: str, salary_min=None, salary_max=None) -> int:
    """Best-effort estimate of years of experience required.

    Looks for explicit patterns in the description/title first, otherwise falls
    back to a conservative default. Never returns None so downstream analytics
    (which expect an int) keep working.
    """
    text = f"{title or ''} {description or ''}"
    # e.g. "5 to 8 years", "5-8 years", "5 years of experience", "5+ yrs exp"
    patterns = [
        r"(\d{1,2})\s*-{1,2}\s*(\d{1,2})\s*(?:years?|yrs?)",
        r"(\d{1,2})\s*(?:years?|yrs?)+",
        r"(?:experience|exp)\D{0,12}(\d{1,2})",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            values = [int(x) for x in m.groups() if x and x.isdigit()]
            if values:
                if len(values) >= 2:
                    return (values[0] + values[1]) // 2
                return values[0]
    # Weak estimate from salary magnitude (in INR LPA), used only as a hint.
    if isinstance(salary_max, (int, float)) and salary_max > 0:
        if salary_max >= 3000000:
            return 6
        if salary_max >= 1500000:
            return 3
    return 1


def format_salary_range(salary_min, salary_max, salary_raw: str) -> str:
    """Produce a human-readable salary string compatible with the legacy
    ``salary_range`` field (e.g. '8-12 LPA', '3-5 LPA')."""
    if salary_raw and str(salary_raw).strip():
        return str(salary_raw).strip()
    if isinstance(salary_min, (int, float)) and isinstance(salary_max, (int, float)):
        if salary_min >= 0 and salary_max >= 0:
            return f"{round(salary_min / 100000, 1)}-{round(salary_max / 100000, 1)} LPA"
    if isinstance(salary_max, (int, float)) and salary_max > 0:
        return f"Up to {round(salary_max / 100000, 1)} LPA"
    return "Not disclosed"


def to_app_job(normalized: dict, db=None, source: str = "unknown") -> dict:
    """Convert a provider-neutral job dict into the application's document shape.

    Preserves all legacy fields (title, company, skills, experience_years,
    location, salary_range, posting_date, job_type, domain) and adds provenance
    metadata used by the ingestion system.
    """
    now = datetime.utcnow().isoformat()

    reqs = normalized.get("requirements") or []
    title = normalized.get("title") or ""
    description = normalized.get("description") or ""

    # Adzuna gives few explicit requirement tokens; enrich from the description's
    # known skill vocabulary so the skill analysis stays useful.
    enriched = _extract_skills_from_text(title + " " + description)
    combined = list(dict.fromkeys(list(reqs) + enriched))

    normalized_skills = normalize_skill_list(combined, db=db)

    salary_min = normalized.get("salaryMin")
    salary_max = normalized.get("salaryMax")
    salary_raw = normalized.get("salaryRaw")
    salary_range = format_salary_range(salary_min, salary_max, salary_raw)

    integrated_posted = normalized.get("postedAt") or now
    try:
        posting_date = datetime.fromisoformat(str(integrated_posted).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        posting_date = datetime.utcnow()
    posting_date_str = posting_date.strftime("%Y-%m-%d")

    return {
        "source": source,
        "externalId": str(normalized.get("externalId") or ""),
        "title": title,
        "company": normalized.get("company") or "",
        "skills": ", ".join(normalized_skills),
        "skills_list": normalized_skills,
        "experience_years": parse_experience_years(
            title, description, salary_min=salary_min, salary_max=salary_max
        ),
        "location": normalized.get("location") or "",
        "salary_range": salary_range,
        "posting_date": posting_date_str,
        "domain": normalized.get("category") or "",
        "job_type": "Full-time",
        "description": description,
        "postedAt": integrated_posted,
        "lastSeenAt": now,
        "lastUpdatedAt": now,
        "status": "active",
    }


_SKILL_WORDS = [
    "Python", "Java", "JavaScript", "TypeScript", "SQL", "React", "Node.js",
    "Docker", "Kubernetes", "AWS", "Azure", "Git", "GitHub", "GitLab",
    "MongoDB", "PostgreSQL", "Redis", "Kafka", "Spark", "Hadoop",
    "TensorFlow", "PyTorch", "Machine Learning", "Deep Learning", "AI",
    "Django", "Flask", "FastAPI", "Spring Boot", "Angular", "Vue.js", "Flutter",
    "Terraform", "Jenkins", "CI/CD", "Linux", "Excel", "Tableau", "Power BI",
    "Communication", "Leadership", "Agile", "Scrum", "Problem Solving", "C++", "Go",
    "REST API", "GraphQL", "Microservices", "System Design", "Pandas", "Numpy",
]


def _extract_skills_from_text(text: str) -> list:
    """Scan free text for known skill vocabulary (case-insensitive)."""
    found = []
    lower = text.lower()
    for skill in _SKILL_WORDS:
        if skill.lower() in lower:
            found.append(skill)
    return found
