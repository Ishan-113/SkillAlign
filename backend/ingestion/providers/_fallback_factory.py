"""Minimal synthetic job generator used only as a last-resort fallback if the
existing scripts/scraper module cannot be imported. Produces the same shape as
the mock provider expects.
"""

import random
from datetime import datetime, timedelta

_LOCATIONS = ["Mumbai", "Bangalore", "Pune", "Hyderabad", "Chennai", "Delhi", "Noida", "Kolkata"]
_TITLES = ["Software Engineer", "Backend Developer", "Data Analyst", "DevOps Engineer",
           "Frontend Developer", "Machine Learning Engineer", "Full Stack Developer", "Cloud Engineer"]
_COMPANIES = ["TCS", "Infosys", "Wipro", "Accenture", "Amazon India", "Google India", "Cognizant", "Deloitte"]
_TITLES_SKILLS = {
    "Software Engineer": ["Python", "Java", "SQL", "Git", "Docker"],
    "Backend Developer": ["Node.js", "Python", "SQL", "REST API", "Docker"],
    "Data Analyst": ["Python", "SQL", "Excel", "Pandas", "Tableau"],
    "DevOps Engineer": ["Docker", "Kubernetes", "AWS", "Jenkins", "Git"],
    "Frontend Developer": ["JavaScript", "React", "HTML", "CSS", "Git"],
    "Machine Learning Engineer": ["Python", "TensorFlow", "Pandas", "SQL", "AWS"],
    "Full Stack Developer": ["JavaScript", "React", "Node.js", "SQL", "Git"],
    "Cloud Engineer": ["AWS", "Azure", "Docker", "Kubernetes", "Terraform"],
}


def generate_minimal_jobs(target_count: int = 200) -> list:
    jobs = []
    for i in range(1, target_count + 1):
        title = random.choice(_TITLES)
        exp = random.choices([random.randint(0, 5), random.randint(6, 12)], weights=[70, 30])[0]
        posting_date = (datetime.now() - timedelta(days=random.randint(0, 30))).strftime("%Y-%m-%d")
        jobs.append({
            "job_id": i,
            "title": title,
            "company": random.choice(_COMPANIES),
            "skills": ", ".join(random.sample(_TITLES_SKILLS[title], random.randint(3, len(_TITLES_SKILLS[title])))),
            "experience_years": exp,
            "location": random.choice(_LOCATIONS),
            "salary_range": f"{random.randint(3, 8)}-{random.randint(9, 20)} LPA",
            "posting_date": posting_date,
            "job_type": random.choice(["Full-time", "Contract", "Remote"]),
            "domain": random.choice(["Software Development", "Data & AI", "Cloud & DevOps"]),
        })
    return jobs
