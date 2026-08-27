import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routes.auth import router as auth_router
from routes.skillgap import router as skillgap_router
from routes.data import router as data_router
from routes.marketintel import router as marketintel_router
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
app.include_router(skillgap_router, prefix="/api", tags=["Skill Gap"])
app.include_router(data_router, prefix="/api", tags=["Data"])
app.include_router(marketintel_router, prefix="/api", tags=["Market Intelligence"])


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "PS 26134 API", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
