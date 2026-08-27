"""Market intelligence endpoints (Dashboard, Industry Demand, Recommendations,
Career Guidance) powered by the LIVE MongoDB job dataset.

These endpoints read only from MongoDB (the cached ingestion source) and never
trigger external API calls, so opening the app never consumes provider quota.

Sector is derived from each job's ``domain`` field (the Adzuna category label),
falling back to a title-keyword classification. District is derived from the
job's ``location`` string (best-effort city/sub-locality normalization).
"""

import os
import re
from pathlib import Path
from collections import Counter, defaultdict

from fastapi import APIRouter, Query
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB_NAME", "sih134")

router = APIRouter()

# Map of Adzuna domain/category labels to a normalized sector name.
DOMAIN_SECTOR_MAP = {
    "software engineering": "Software & IT",
    "it & telecoms": "Software & IT",
    "it": "Software & IT",
    "telecoms": "Software & IT",
    "engineering": "Engineering",
    "manufacturing": "Engineering",
    "accountancy": "Finance & Accounting",
    "banking": "Finance & Accounting",
    "finance": "Finance & Accounting",
    "insurance": "Finance & Accounting",
    "consultancy": "Consulting & Management",
    "management": "Consulting & Management",
    "health": "Healthcare",
    "healthcare": "Healthcare",
    "nursing": "Healthcare",
    "medical": "Healthcare",
    "hospitality": "Hospitality & Travel",
    "leisure travel": "Hospitality & Travel",
    "travel": "Hospitality & Travel",
    "retail": "Retail & Sales",
    "sales": "Retail & Sales",
    "marketing": "Marketing & Media",
    "media": "Marketing & Media",
    "creative": "Marketing & Media",
    "digital": "Marketing & Media",
    "graduate": "Graduate & Entry Level",
    "hr": "HR & Admin",
    "admin": "HR & Admin",
    "legal": "Legal",
    "logistics": "Logistics & Supply Chain",
    "supply chain": "Logistics & Supply Chain",
    "education": "Education",
    "science": "Science & Research",
    "property": "Real Estate",
    "construction": "Construction",
    "energy": "Energy & Utilities",
    "utilities": "Energy & Utilities",
    "security": "Security & Defence",
    "public sector": "Public Sector",
    "other": "Other",
}

# Fallback: map from title keywords to a sector when domain is empty/unknown.
TITLE_SECTOR_KEYWORDS = {
    "Software & IT": ["developer", "engineer", "software", "python", "java", "frontend", "backend", "full stack", "devops", "data", "cloud", "ai", "ml", "programmer"],
    "Finance & Accounting": ["accountant", "finance", "audit", "tax", "bank", "analyst"],
    "Marketing & Media": ["marketing", "media", "content", "design", "social media"],
    "Retail & Sales": ["sales", "retail", "account executive", "business development"],
    "Engineering": ["mechanical", "civil", "electrical", "electronics", "manufacturing", "process"],
    "Healthcare": ["nurse", "doctor", "medical", "pharma", "clinical", "care"],
}


def _sector_for(domain: str, title: str) -> str:
    domain = (domain or "").strip()
    if domain:
        low = domain.lower()
        for key, sector in DOMAIN_SECTOR_MAP.items():
            if key in low:
                return sector
    # fallback by title
    tt = (title or "").lower()
    for sector, kws in TITLE_SECTOR_KEYWORDS.items():
        if any(kw in tt for kw in kws):
            return sector
    return "Other"


# Common Indian metro/city names to normalize raw location strings into a district-like label.
CITY_ALIASES = [
    ("bangalore", "Bengaluru"), ("bengaluru", "Bengaluru"), ("indiranagar", "Bengaluru"),
    ("hyderabad", "Hyderabad"), ("secunderabad", "Hyderabad"),
    ("chennai", "Chennai"), ("pune", "Pune"), ("mumbai", "Mumbai"), ("bombay", "Mumbai"),
    ("delhi", "Delhi NCR"), ("noida", "Delhi NCR"), ("gurgaon", "Delhi NCR"), ("gurugram", "Delhi NCR"),
    ("ghaziabad", "Delhi NCR"), ("faridabad", "Delhi NCR"),
    ("kolkata", "Kolkata"), ("calcutta", "Kolkata"),
    ("ahmedabad", "Ahmedabad"), ("gandhinagar", "Ahmedabad"),
    ("kochi", "Kochi"), ("cochin", "Kochi"),
    ("jaipur", "Jaipur"), ("lucknow", "Lucknow"), ("kanpur", "Kanpur"),
    ("chandigarh", "Chandigarh"), ("indore", "Indore"), ("bhopal", "Bhopal"),
    ("nagpur", "Nagpur"), ("surat", "Surat"), ("visakhapatnam", "Visakhapatnam"),
    ("guwahati", "Guwahati"), ("bhubaneswar", "Bhubaneswar"), ("coimbatore", "Coimbatore"),
    ("mysore", "Mysuru"), ("thiruvananthapuram", "Thiruvananthapuram"),
]


def _district_for(location: str, title: str = "") -> str:
    low = (location or title or "").lower()
    for alias, city in CITY_ALIASES:
        if alias in low:
            return city
    # If nothing matches, return a title-cased token if a city-ish token exists.
    if location:
        tokens = [t for t in re.split(r"[,/()]", location) if t.strip()]
        if tokens:
            return tokens[0].strip().title()
    return "Other"


class _DB:
    """Lazy per-request sync MongoDB access (mirrors data.py pattern)."""

    def __init__(self):
        self._client = None

    def get(self):
        if self._client is None:
            self._client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=6000)
        return self._client[DB_NAME]

    def close(self):
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None


def _load_jobs(db, district=None, sector=None):
    """Return (jobs, sectors_set). Applies district/sector filter if given."""
    query = {"$or": [{"status": "active"}, {"status": {"$exists": False}}]}
    jobs = list(db["jobs"].find(query, {"_id": 0}))
    sectors = set()
    out = []
    for j in jobs:
        sec = _sector_for(j.get("domain", ""), j.get("title", ""))
        sectors.add(sec)
        if sector and sec != sector:
            continue
        dist = _district_for(j.get("location", ""), j.get("title", ""))
        if district and dist != district:
            continue
        out.append(j)
    return out, sectors


def _salary_value(job) -> int:
    """Extract a numeric annual salary (INR) from salary_range string if possible."""
    raw = str(job.get("salary_range") or "")
    m = re.search(r"(\d[\d,.]*)\s*-\s*(\d[\d,.]*)\s*LPA", raw)
    if m:
        try:
            mid = (float(m.group(1).replace(",", "")) + float(m.group(2).replace(",", ""))) / 2
            return int(mid * 100000)
        except Exception:
            return 0
    m = re.search(r"(\d[\d,.]*)\s*LPA", raw)
    if m:
        try:
            return int(float(m.group(1).replace(",", "")) * 100000)
        except Exception:
            return 0
    m = re.search(r"(?:₹|INR)?\s?([\d,]+)\s*-\s*([\d,]+)", raw.replace(",", ""))
    if m:
        try:
            return (int(m.group(1)) + int(m.group(2))) // 2
        except Exception:
            return 0
    return 0


dbh = _DB()


@router.get("/districts")
async def list_districts():
    db = dbh.get()
    try:
        jobs = list(db["jobs"].find({}, {"_id": 0, "location": 1, "title": 1}))
        counts = Counter(_district_for(j.get("location", ""), j.get("title", "")) for j in jobs)
        districts = [{"district": d, "count": c, "percentage": round(c / max(len(jobs), 1) * 100, 1)}
                     for d, c in counts.most_common()]
        return {"districts": districts, "total": len(districts)}
    finally:
        dbh.close()


@router.get("/districts/{district}")
async def district_detail(district: str):
    db = dbh.get()
    try:
        jobs, _ = _load_jobs(db, district=district)
        sectors = Counter(_sector_for(j.get("domain", ""), j.get("title", "")) for j in jobs)
        comp = Counter(j.get("company", "") for j in jobs if j.get("company"))
        skills = Counter()
        for j in jobs:
            for s in str(j.get("skills", "")).split(","):
                s = s.strip()
                if s:
                    skills[s] += 1
        return {
            "district": district,
            "total_jobs": len(jobs),
            "top_sectors": [{"sector": s, "count": c} for s, c in sectors.most_common(8)],
            "top_companies": [{"company": c, "count": n} for c, n in comp.most_common(8)],
            "top_skills": [{"skill": s, "count": c} for s, c in skills.most_common(12)],
        }
    finally:
        dbh.close()


@router.get("/sectors")
async def list_sectors():
    db = dbh.get()
    try:
        jobs = list(db["jobs"].find({}, {"_id": 0, "domain": 1, "title": 1}))
        counts = Counter(_sector_for(j.get("domain", ""), j.get("title", "")) for j in jobs)
        sectors = [{"sector": s, "count": c, "percentage": round(c / max(len(jobs), 1) * 100, 1)}
                   for s, c in counts.most_common()]
        return {"sectors": sectors, "total": len(sectors)}
    finally:
        dbh.close()


@router.get("/dashboard")
async def dashboard(
    district: str = Query(None),
    sector: str = Query(None),
    time_period: str = Query("all", description="all|7d|30d"),
):
    db = dbh.get()
    try:
        jobs, sectors = _load_jobs(db, district=district, sector=sector)
        if time_period == "7d" or time_period == "30d":
            from datetime import datetime, timedelta
            days = 7 if time_period == "7d" else 30
            cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
            jobs = [j for j in jobs if j.get("posting_date", "") >= cutoff]

        total = len(jobs)
        skills = Counter()
        for j in jobs:
            for s in str(j.get("skills", "")).split(","):
                s = s.strip()
                if s:
                    skills[s] += 1

        companies = Counter(j.get("company", "") for j in jobs if j.get("company"))
        exp_ranges = {"0-2 yrs": 0, "3-5 yrs": 0, "6-8 yrs": 0, "8+ yrs": 0}
        for j in jobs:
            e = j.get("experience_years") or 0
            if e <= 2:
                exp_ranges["0-2 yrs"] += 1
            elif e <= 5:
                exp_ranges["3-5 yrs"] += 1
            elif e <= 8:
                exp_ranges["6-8 yrs"] += 1
            else:
                exp_ranges["8+ yrs"] += 1

        salaries = sorted((_salary_value(j) for j in jobs if _salary_value(j) > 0), reverse=True)
        avg_salary = round(sum(salaries) / len(salaries)) if salaries else 0

        # Trend: job count by posting month (last 12 distinct present months)
        month_counts = Counter(j.get("posting_date", "")[:7] for j in jobs if j.get("posting_date"))
        trend = [{"period": m, "count": c} for m, c in sorted(month_counts.items())]

        # Location distribution (top 10 areas)
        loc_counts = Counter(_district_for(j.get("location", ""), j.get("title", "")) for j in jobs)
        locations = [{"location": loc, "count": c, "percentage": round(c / max(total, 1) * 100, 1)}
                     for loc, c in loc_counts.most_common(10)]

        return {
            "filters": {"district": district, "sector": sector, "time_period": time_period},
            "summary": {
                "total_jobs": total,
                "unique_skills": len(skills),
                "top_companies_count": len(companies),
                "average_salary": avg_salary,
                "sectors_present": sorted(sectors),
            },
            "top_skills": [{"skill": s, "count": c, "percentage": round(c / max(total, 1) * 100, 1)}
                           for s, c in skills.most_common(15)],
            "companies": [{"company": c, "count": n} for c, n in companies.most_common(10)],
            "experience_distribution": [{"range": r, "count": c} for r, c in exp_ranges.items()],
            "locations": locations,
            "job_trend": trend[-12:] if trend else [],
        }
    finally:
        dbh.close()


@router.get("/industry-demand")
async def industry_demand(
    district: str = Query(None),
    sector: str = Query(None),
):
    db = dbh.get()
    try:
        jobs, _ = _load_jobs(db, district=district, sector=sector)
        skills = Counter()
        for j in jobs:
            for s in str(j.get("skills", "")).split(","):
                s = s.strip()
                if s:
                    skills[s] += 1

        # average salary per skill (best-effort)
        skill_salary = defaultdict(list)
        for j in jobs:
            for s in str(j.get("skills", "")).split(","):
                s = s.strip()
                if s and _salary_value(j) > 0:
                    skill_salary[s].append(_salary_value(j))

        demand = []
        for s, c in skills.most_common(20):
            vals = skill_salary.get(s) or []
            demand.append({
                "skill": s,
                "count": c,
                "percentage": round(c / max(len(jobs), 1) * 100, 1) if jobs else 0,
                "avg_salary": round(sum(vals) / len(vals)) if vals else 0,
            })

        return {"industry_demand": demand, "total_jobs": len(jobs)}
    finally:
        dbh.close()


@router.get("/recommendations")
async def recommendations(
    district: str = Query(None),
    sector: str = Query(None),
    course_id: str = Query(None),
):
    db = dbh.get()
    try:
        jobs, _ = _load_jobs(db, district=district, sector=sector)
        skills = Counter()
        for j in jobs:
            for s in str(j.get("skills", "")).split(","):
                s = s.strip()
                if s:
                    skills[s] += 1
        top = [s for s, _ in skills.most_common(12)]

        # Simple course/skill recommendation mapping
        recommendations = []
        for s in top[:8]:
            recommendations.append({
                "skill": s,
                "demand_count": skills[s],
                "suggested_topics": _topics_for_skill(s),
                "level": "Foundational" if s.lower() in {"sql", "python", "java", "html", "css", "javascript"} else "Intermediate/Advanced",
            })

        return {
            "recommendations": recommendations,
            "filters": {"district": district, "sector": sector, "course_id": course_id},
            "top_demand_skills": top,
        }
    finally:
        dbh.close()


def _career_recommendation(missing: list, education: str, preferred_role: str) -> str:
    if not missing:
        return (
            f"You are already aligned with current market demand. Consider targeting "
            f"roles like '{preferred_role}' and emphasizing your existing skills in "
            f"interviews and your portfolio."
        )
    edu = (education or "").lower()
    ease = "you may already be familiar with, given your background" if ("engineer" in edu or "b.tech" in edu or "bsc" in edu or "mca" in edu or "it" in edu) else "foundational skills that are in high demand and quick to learn"
    top = ", ".join(missing[:4])
    return (
        f"To become competitive for roles like '{preferred_role}', focus next on: {top}. "
        f"These are {ease}. Pair each with a hands-on project and a recognized "
        f"certification, then tailor your resume keywords to the job descriptions listed "
        f"on the Industry Demand page."
    )


def _topics_for_skill(skill: str) -> list:
    s = skill.lower()
    catalog = {
        "python": ["Python Essentials", "OOP with Python", "Automation", "Data Structures"],
        "sql": ["SQL Queries", "Database Design", "Data Modeling", "Optimization"],
        "java": ["Core Java", "Spring Boot", "Microservices", "OOP"],
        "javascript": ["ES6+", "React", "Node.js", "Web APIs"],
        "cloud": ["AWS/Azure Basics", "Docker", "Kubernetes", "CI/CD"],
        "data": ["Stats", "Pandas", "SQL", "Visualization"],
        "ai": ["Machine Learning", "LLMs", "Prompt Engineering", "MLOps"],
        "ml": ["Machine Learning", "Deep Learning", "Scikit-learn", "Model Deployment"],
        "devops": ["Docker", "Kubernetes", "GitHub Actions", "Monitoring"],
        "docker": ["Docker", "Containers", "Kubernetes", "Microservices"],
        "react": ["React Hooks", "State Management", "REST", "Component Design"],
        "node": ["Node.js", "Express", "REST APIs", "Async Programming"],
    }
    for key, topics in catalog.items():
        if key in s:
            return topics
    return ["Foundational concepts", "Hands-on projects", "Industry tools", "Certification/exam prep"]


@router.post("/career-guidance")
async def career_guidance(payload: dict):
    location = str(payload.get("location") or "").strip()
    education = str(payload.get("education") or "").strip()
    current_skills = [str(s).strip() for s in (payload.get("current_skills") or []) if str(s).strip()]
    preferred_sector = str(payload.get("preferred_sector") or "").strip()
    preferred_role = str(payload.get("preferred_role") or "").strip()

    db = dbh.get()
    try:
        jobs, _ = _load_jobs(db, district=location or None, sector=preferred_sector or None)
        skills = Counter()
        for j in jobs:
            for s in str(j.get("skills", "")).split(","):
                s = s.strip()
                if s:
                    skills[s] += 1

        current_set = set(s.lower() for s in current_skills)
        in_demand = [s for s, _ in skills.most_common(20)]
        missing = [s for s in in_demand if s.lower() not in current_set][:8]

        top_roles = Counter(j.get("title", "") for j in jobs if j.get("title")).most_common(6)
        top_companies = Counter(j.get("company", "") for j in jobs if j.get("company")).most_common(6)

        suggested_sector = preferred_sector or _sector_for("", top_roles[0][0] if top_roles else "")

        return {
            "profile": {
                "location": location or "Any",
                "education": education or "Not specified",
                "current_skills": current_skills,
                "preferred_sector": preferred_sector or suggested_sector or "General",
                "preferred_role": preferred_role or (top_roles[0][0] if top_roles else "General"),
            },
            "analysis": {
                "jobs_considered": len(jobs),
                "in_demand_skills": in_demand[:12],
                "skills_to_learn": missing,
                "top_roles": [{"role": r, "count": c} for r, c in top_roles],
                "top_companies": [{"company": c, "count": n} for c, n in top_companies],
            },
            "recommendation": _career_recommendation(missing, education, preferred_role or (top_roles[0][0] if top_roles else "")),
        }
    finally:
        dbh.close()
