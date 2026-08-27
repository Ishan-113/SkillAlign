from fastapi import APIRouter
from fastapi.responses import JSONResponse
from services.mongodb import get_db

router = APIRouter()


def check_db():
    db = get_db()
    if db is None:
        return None, JSONResponse({"error": "Database not connected"}, status_code=503)
    return db, None


@router.get("/insights")
async def get_key_insights():
    db, err = check_db()
    if err:
        return err

    jobs = await db.jobs.find({}).to_list(length=None)

    total_jobs = len(jobs)
    if total_jobs == 0:
        return {"error": "No jobs found in database"}

    skill_count = {}
    for job in jobs:
        for skill in job["skills"].split(","):
            skill = skill.strip()
            skill_count[skill] = skill_count.get(skill, 0) + 1

    top_skill = max(skill_count.items(), key=lambda x: x[1]) if skill_count else ("N/A", 0)

    location_count = {}
    for job in jobs:
        loc = job["location"]
        location_count[loc] = location_count.get(loc, 0) + 1

    top_location = max(location_count.items(), key=lambda x: x[1]) if location_count else ("N/A", 0)

    company_count = {}
    for job in jobs:
        comp = job["company"]
        company_count[comp] = company_count.get(comp, 0) + 1

    avg_exp = sum(job["experience_years"] for job in jobs) / total_jobs

    exp_ranges = {"Fresher (0-2 yrs)": 0, "Mid-level (3-5 yrs)": 0, "Senior (6+ yrs)": 0}
    for job in jobs:
        exp = job["experience_years"]
        if exp <= 2:
            exp_ranges["Fresher (0-2 yrs)"] += 1
        elif exp <= 5:
            exp_ranges["Mid-level (3-5 yrs)"] += 1
        else:
            exp_ranges["Senior (6+ yrs)"] += 1

    return {
        "summary": {
            "total_jobs_analyzed": total_jobs,
            "unique_skills_found": len(skill_count),
            "total_locations": len(location_count),
            "total_companies": len(company_count),
            "average_experience_years": round(avg_exp, 1),
        },
        "top_insights": [
            {
                "title": "Most In-Demand Skill",
                "value": top_skill[0],
                "detail": f"Found in {top_skill[1]} out of {total_jobs} job postings ({round(top_skill[1]/total_jobs*100, 1)}%)",
                "icon": "star",
            },
            {
                "title": "Top Hiring Location",
                "value": top_location[0],
                "detail": f"{top_location[1]} job postings ({round(top_location[1]/total_jobs*100, 1)}%)",
                "icon": "map-pin",
            },
            {
                "title": "Experience Demand",
                "value": f"{round(avg_exp, 1)} years average",
                "detail": f"Most roles require {max(exp_ranges.items(), key=lambda x: x[1])[0]}",
                "icon": "briefcase",
            },
            {
                "title": "Skill Gap Alert",
                "value": f"{len(skill_count)} unique skills",
                "detail": "High diversity in required skills - upskilling is critical",
                "icon": "alert-triangle",
            },
        ],
        "experience_distribution": exp_ranges,
        "hiring_trends": {
            "top_companies": sorted(company_count.items(), key=lambda x: x[1], reverse=True)[:5],
            "top_locations": sorted(location_count.items(), key=lambda x: x[1], reverse=True)[:5],
        },
    }
