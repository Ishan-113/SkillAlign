from fastapi import APIRouter
from services.mongodb import get_db

router = APIRouter()


@router.get("/locations")
async def get_location_distribution():
    db = get_db()
    rows = await db.jobs.find({}, {"location": 1, "_id": 0}).to_list(length=None)

    location_count = {}
    for row in rows:
        loc = row["location"]
        location_count[loc] = location_count.get(loc, 0) + 1

    sorted_locations = sorted(location_count.items(), key=lambda x: x[1], reverse=True)

    return {
        "total_locations": len(location_count),
        "distribution": [
            {"location": loc, "count": c, "percentage": round(c / len(rows) * 100, 1) if rows else 0}
            for loc, c in sorted_locations
        ],
        "total_jobs": len(rows),
    }


@router.get("/locations/companies")
async def get_companies_by_location():
    db = get_db()
    rows = await db.jobs.find({}, {"location": 1, "company": 1, "_id": 0}).to_list(length=None)

    loc_companies = {}
    for row in rows:
        loc = row["location"]
        company = row["company"]
        if loc not in loc_companies:
            loc_companies[loc] = set()
        loc_companies[loc].add(company)

    return {
        "companies_by_location": {
            loc: list(companies) for loc, companies in loc_companies.items()
        }
    }
