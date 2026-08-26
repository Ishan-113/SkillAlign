from fastapi import APIRouter
from services.mongodb import get_db

router = APIRouter()


@router.get("/experience")
async def get_experience_distribution():
    db = get_db()
    rows = await db.jobs.find({}, {"experience_years": 1, "_id": 0}).to_list(length=None)

    exp_ranges = {"0-2 years": 0, "3-5 years": 0, "6-8 years": 0, "8+ years": 0}

    for row in rows:
        exp = row["experience_years"]
        if exp <= 2:
            exp_ranges["0-2 years"] += 1
        elif exp <= 5:
            exp_ranges["3-5 years"] += 1
        elif exp <= 8:
            exp_ranges["6-8 years"] += 1
        else:
            exp_ranges["8+ years"] += 1

    total = len(rows)
    avg_exp = sum(row["experience_years"] for row in rows) / total if total else 0

    return {
        "distribution": [
            {"range": k, "count": v, "percentage": round(v / total * 100, 1) if total else 0}
            for k, v in exp_ranges.items()
        ],
        "average_experience": round(avg_exp, 1),
        "total_jobs": total,
    }


@router.get("/experience/salary")
async def get_salary_by_experience():
    db = get_db()
    rows = await db.jobs.find({}, {"experience_years": 1, "salary_range": 1, "_id": 0}).to_list(length=None)

    salary_map = {}
    for row in rows:
        exp = row["experience_years"]
        salary = row["salary_range"]
        if exp not in salary_map:
            salary_map[exp] = []
        salary_map[exp].append(salary)

    return {
        "salary_by_experience": [
            {"experience_years": k, "salary_ranges": v}
            for k, v in sorted(salary_map.items())
        ]
    }
