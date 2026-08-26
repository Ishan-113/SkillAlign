from fastapi import APIRouter
from fastapi.responses import JSONResponse
from services.mongodb import get_db

router = APIRouter()


def check_db():
    db = get_db()
    if not db:
        return None, JSONResponse({"error": "Database not connected. Check MongoDB Atlas IP whitelist."}, status_code=503)
    return db, None


@router.get("/skills")
async def get_skills_analysis():
    db, err = check_db()
    if err:
        return err

    rows = await db.jobs.find({}, {"skills": 1, "_id": 0}).to_list(length=None)

    skill_count = {}
    for row in rows:
        for skill in row["skills"].split(","):
            skill = skill.strip()
            skill_count[skill] = skill_count.get(skill, 0) + 1

    sorted_skills = sorted(skill_count.items(), key=lambda x: x[1], reverse=True)
    total = len(rows)

    return {
        "total_unique_skills": len(skill_count),
        "top_skills": [
            {"skill": s, "count": c, "percentage": round(c / total * 100, 1) if total else 0}
            for s, c in sorted_skills[:15]
        ],
        "all_skills": skill_count,
        "total_jobs_analyzed": total,
    }


@router.get("/skills/top")
async def get_top_skills(limit: int = 10):
    db, err = check_db()
    if err:
        return err

    rows = await db.jobs.find({}, {"skills": 1, "_id": 0}).to_list(length=None)

    skill_count = {}
    for row in rows:
        for skill in row["skills"].split(","):
            skill = skill.strip()
            skill_count[skill] = skill_count.get(skill, 0) + 1

    sorted_skills = sorted(skill_count.items(), key=lambda x: x[1], reverse=True)[:limit]
    total = len(rows)

    return {
        "top_skills": [
            {"skill": s, "count": c, "percentage": round(c / total * 100, 1) if total else 0}
            for s, c in sorted_skills
        ]
    }
