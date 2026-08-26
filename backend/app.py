import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routes.skills import router as skills_router
from routes.experience import router as experience_router
from routes.locations import router as locations_router
from routes.insights import router as insights_router
from routes.auth import router as auth_router
from routes.skillgap import router as skillgap_router
from services.database import init_db
from services.mongodb import connect_db, close_db

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    try:
        await connect_db()
    except Exception as e:
        print(f"MongoDB not available, using SQLite fallback: {e}")
    yield
    await close_db()


app = FastAPI(
    title="PS 26134 - Skill Development & Industry Alignment API",
    description="Smart India Hackathon 2026 - Government of Maharashtra",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(skills_router, prefix="/api", tags=["Skills"])
app.include_router(experience_router, prefix="/api", tags=["Experience"])
app.include_router(locations_router, prefix="/api", tags=["Locations"])
app.include_router(insights_router, prefix="/api", tags=["Insights"])
app.include_router(skillgap_router, prefix="/api", tags=["Skill Gap"])


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "PS 26134 API", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
