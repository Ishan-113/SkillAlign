import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from datetime import datetime, timezone

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


@app.get("/api/db-status")
async def db_status():
    """Diagnostics: report MONGO env presence and test a real Atlas connection.

    Returns the actual error so the live Render failure can be diagnosed from a
    browser without shell access to the service.
    """
    from pymongo import MongoClient
    import traceback

    uri = os.getenv("MONGO_URI", "")
    db_name = os.getenv("MONGO_DB_NAME", "sih134")

    info = {
        "mongo_uri_set": bool(uri),
        "mongo_uri_scheme": uri.split("://")[0] if uri else None,
        "mongo_uri_host": (uri.split("://")[-1].split("?")[0].split("@")[-1] if uri else None),
        "mongo_db_name": db_name,
        "server_timeout_ms": 15000,
    }

    if not uri:
        info["result"] = "MONGO_URI env var is NOT set on this service"
        return info

    client = None
    try:
        effective_uri = uri
        # env vars may be double-quoted if pasted into the dashboard
        if effective_uri.startswith('"') and effective_uri.endswith('"'):
            effective_uri = effective_uri[1:-1]
        client = MongoClient(effective_uri, serverSelectionTimeoutMS=15000, connectTimeoutMS=10000)
        ping = client[db_name].command("ping")
        info["result"] = "connected"
        info["ping"] = ping.get("ok")
        info["db_names"] = client.list_database_names()
    except Exception as e:
        info["result"] = "ERROR"
        info["error_type"] = type(e).__name__
        info["error_message"] = str(e)
        info["traceback"] = traceback.format_exc(limit=3)
    finally:
        if client is not None:
            client.close()
    return info


@app.api_route("/api/admin/refresh-jobs", methods=["GET", "POST"])
async def admin_refresh_jobs(request: Request):
    """Trigger one job-ingestion pass (used by a free external cron scheduler).

    Protected by the INGESTION_TOKEN env var: the caller must send it in the
    ``X-Ingestion-Token`` header. This lets an external free scheduler (e.g.
    cron-job.org) auto-refresh MongoDB on an interval without paying for a
    Render cron, while keeping the endpoint private. It writes straight to the
    ``jobs`` collection (upsert, de-duped by source+externalId) and records an
    ``update_logs`` entry — exactly like the GitHub Actions entry point.
    """
    expected = os.getenv("INGESTION_TOKEN", "")
    provided = request.headers.get("x-ingestion-token", "")
    if not expected or provided != expected:
        return JSONResponse({"detail": "unauthorized"}, status_code=401)

    import asyncio as _asyncio
    from services.mongodb import get_ingestion_collections, build_indexes
    from ingestion.job_ingestion import run_job_update

    def _run():
        database = get_ingestion_collections()
        try:
            build_indexes(database)
            result = run_job_update(database)
            return result.to_dict()
        finally:
            client = getattr(database, "_sih_client", None)
            if client:
                client.close()

    result = await _asyncio.to_thread(_run)
    return {
        "status": "ok",
        "refreshed_at": datetime.now(timezone.utc).isoformat(),
        "result": result,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
