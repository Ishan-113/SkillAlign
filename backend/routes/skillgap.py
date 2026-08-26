import os
import sys
import json
from pathlib import Path
from collections import Counter, defaultdict
from fastapi import APIRouter, Query
from typing import Optional
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB_NAME", "sih134")

router = APIRouter()

INDUSTRY_NEEDS = {
    "programming": ["Python", "Java", "JavaScript", "TypeScript", "Go", "Rust", "Kotlin", "Swift"],
    "frameworks": ["React", "Angular", "Vue.js", "Node.js", "Spring Boot", "Django", "Flask", "FastAPI", "Next.js", ".NET"],
    "cloud": ["AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform", "Ansible", "Helm"],
    "data": ["SQL", "NoSQL", "Spark", "Hadoop", "Airflow", "Kafka", "MongoDB", "Redis", "Elasticsearch"],
    "ml_ai": ["TensorFlow", "PyTorch", "Scikit-learn", "NLP", "Computer Vision", "Generative AI", "LLMs", "MLOps"],
    "devops": ["CI/CD", "Jenkins", "GitHub Actions", "GitLab CI", "ArgoCD", "Prometheus", "Grafana", "Datadog"],
    "security": ["OWASP", "SIEM", "Penetration Testing", "Compliance", "Zero Trust", "SOC"],
    "soft_skills": ["System Design", "API Design", "Agile", "Scrum", "Communication", "Leadership"],
    "web": ["HTML5", "CSS3", "SASS", "REST API", "GraphQL", "WebSocket", "PWA"],
    "mobile": ["React Native", "Flutter", "Kotlin", "Swift", "iOS", "Android"],
    "tools": ["Git", "Jira", "Confluence", "VS Code", "Postman", "Docker Desktop"],
}

TECH_TREND_2026 = {
    "hot_skills": [
        "Generative AI / LLMs", "Prompt Engineering", "RAG Systems",
        "AI Agents", "Vector Databases", "MLOps",
        "Cloud Native Development", "Platform Engineering",
        "Cybersecurity (Zero Trust)", "Data Engineering",
        "Full Stack Development", "System Design",
    ],
    "declining_skills": [
        "Manual Testing", "Waterfall methodology",
        "Basic HTML/CSS only", "Legacy PHP",
        "On-premise only skills", "Boilerplate coding",
    ],
    "emerging_areas": [
        "AI/ML Engineering", "Quantum Computing basics",
        "Edge Computing", "Blockchain for Enterprise",
        "Sustainability Tech", "HealthTech AI",
    ],
}


def get_all_industry_skills():
    all_skills = set()
    for category in INDUSTRY_NEEDS.values():
        all_skills.update(category)
    return all_skills


def _get_db():
    client = MongoClient(MONGO_URI)
    return client[DB_NAME]


def get_jobs_from_mongodb():
    database = _get_db()
    cursor = database.jobs.find({}, {"_id": 0, "skills": 1, "title": 1})
    return [{"title": j.get("title", ""), "skills": j.get("skills", "")} for j in cursor]


def get_curriculum_from_mongodb(name):
    database = _get_db()
    return database.curricula.find_one({"name": name}, {"_id": 0})


def get_all_curricula_from_mongodb():
    database = _get_db()
    return list(database.curricula.find({}, {"_id": 0, "name": 1, "type": 1, "university": 1, "semesters": 1}))


def analyze_skill_gap(jobs, education_skills, education_source="Custom"):
    industry_skills = Counter()
    for job in jobs:
        for skill in job["skills"].split(","):
            s = skill.strip()
            if s:
                industry_skills[s] += 1

    industry_set = set(industry_skills.keys())
    education_only = education_skills - industry_set
    gap_skills = industry_set - education_skills
    overlap_skills = industry_set & education_skills

    return {
        "curriculum_selected": education_source,
        "total_industry_skills": len(industry_set),
        "total_education_skills": len(education_skills),
        "overlap_count": len(overlap_skills),
        "gap_count": len(gap_skills),
        "gap_skills": sorted(gap_skills),
        "overlap_skills": sorted(overlap_skills),
        "education_only_skills": sorted(education_only),
        "industry_demand": {s: industry_skills[s] for s in sorted(industry_skills, key=industry_skills.get, reverse=True)[:20]},
        "gap_severity": round(len(gap_skills) / max(len(industry_set), 1) * 100, 1),
        "education_skills_list": sorted(education_skills),
    }


def analyze_domain_gap(jobs, education_skills):
    domain_analysis = defaultdict(lambda: {"industry": Counter()})

    domain_skill_map = {
        "Software Development": ["Python", "Java", "JavaScript", "React", "Node.js", "Docker", "SQL", "Git"],
        "Data & AI": ["Python", "SQL", "TensorFlow", "PyTorch", "Tableau", "Spark", "AWS"],
        "Cloud & DevOps": ["AWS", "Docker", "Kubernetes", "Terraform", "Python", "Jenkins", "Linux"],
        "Cybersecurity": ["Network Security", "Python", "SIEM", "CEH", "Linux", "Cloud Security"],
    }

    for job in jobs:
        title = job.get("title", "")
        skills = [s.strip() for s in job["skills"].split(",") if s.strip()]
        for domain, keywords in domain_skill_map.items():
            if any(kw.lower() in title.lower() for kw in domain.split()):
                for skill in skills:
                    domain_analysis[domain]["industry"][skill] += 1

    results = {}
    for domain, data in domain_analysis.items():
        top_industry = data["industry"].most_common(10)
        gap = set(s for s, _ in top_industry) - education_skills
        results[domain] = {
            "top_industry_skills": [{"skill": s, "count": c} for s, c in top_industry],
            "education_gap": sorted(gap),
            "gap_size": len(gap),
        }

    return results


def generate_recommendations(gap_analysis, domain_gap):
    recommendations = []

    if gap_analysis["gap_severity"] > 30:
        recommendations.append({
            "priority": "HIGH",
            "area": "Curriculum Update",
            "recommendation": f"Over {gap_analysis['gap_severity']}% of industry-needed skills are NOT taught in {gap_analysis['curriculum_selected']}. Immediate curriculum revision needed.",
            "skills_to_add": gap_analysis["gap_skills"][:15],
        })

    hot_not_taught = [s for s in TECH_TREND_2026["hot_skills"]
                      if any(g.lower() in s.lower() for g in gap_analysis["gap_skills"])]
    if hot_not_taught:
        recommendations.append({
            "priority": "HIGH",
            "area": "Emerging Technologies",
            "recommendation": f"Hot 2026 skills missing from your education: {', '.join(hot_not_taught[:5])}",
            "skills_to_add": hot_not_taught,
        })

    recommendations.append({
        "priority": "MEDIUM",
        "area": "Practical Experience",
        "recommendation": "University teaches theory but NOT practical tools. Learn Docker, Git, CI/CD, cloud deployment through projects.",
        "skills_to_add": ["Docker", "Git", "CI/CD", "AWS", "System Design", "API Design"],
    })

    recommendations.append({
        "priority": "LOW",
        "area": "Self-Learning Path",
        "recommendation": "Supplement your degree with NPTEL/Coursera courses on ML, Cloud, and Modern Web Development.",
        "skills_to_add": [],
    })

    return recommendations


@router.get("/skill-gap/curricula")
async def list_curricula():
    curricula = get_all_curricula_from_mongodb()
    return {"curricula": curricula, "total": len(curricula)}


@router.get("/skill-gap/personalized")
async def get_personalized_gap(
    curriculum: str = Query(None, description="Curriculum name from MongoDB"),
    skills: str = Query(None, description="Comma-separated custom skills (for 12th/Diploma)"),
    name: str = Query(None, description="Custom education name (for 12th/Diploma)"),
):
    jobs = get_jobs_from_mongodb()
    if not jobs:
        return {"error": "No jobs found in database"}

    if skills:
        education_skills = set(s.strip() for s in skills.split(",") if s.strip())
        education_source = name or "Custom Education"
    elif curriculum:
        curr = get_curriculum_from_mongodb(curriculum)
        if not curr:
            return {"error": f"Curriculum '{curriculum}' not found"}
        education_skills = set(curr.get("all_skills", []))
        education_source = curriculum
    else:
        return {"error": "Provide either 'curriculum' or 'skills' parameter"}

    gap_analysis = analyze_skill_gap(jobs, education_skills, education_source)
    domain_gap = analyze_domain_gap(jobs, education_skills)
    recommendations = generate_recommendations(gap_analysis, domain_gap)

    return {
        "curriculum": education_source,
        "gap_analysis": gap_analysis,
        "domain_gap": domain_gap,
        "recommendations": recommendations,
        "tech_trends": TECH_TREND_2026,
    }
