"""
Job Search & Auto-Apply Agent — FastAPI Backend
"""

import logging
import os
import sys

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure the backend directory is on the Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.config import get_settings
from app.database import init_db
from api.health import router as health_router
from api.settings_api import router as settings_router
from api.profiles import router as profiles_router
from api.resumes import router as resumes_router
from api.jobs import router as jobs_router
from api.matching import router as matching_router
from api.applications import router as applications_router
from api.answer_bank import router as answer_bank_router
from api.analytics import router as analytics_router
from api.events import router as events_router
from services.scheduler import start_scheduler, stop_scheduler

# ─── Logging ─────────────────────────────────────────────────

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("job_agent")


# ─── Lifespan ────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    logger.info("Starting Job Search Agent backend...")
    init_db()
    logger.info("Database initialized.")

    # Log provider status
    if settings.MISTRAL_API_KEY:
        logger.info("Mistral provider: configured (%s / %s)", settings.MISTRAL_STRONG_MODEL, settings.MISTRAL_CHEAP_MODEL)
    else:
        logger.warning("Mistral provider: NOT configured (no API key)")
    if settings.NVIDIA_API_KEY:
        logger.info("NVIDIA provider: configured (%s / %s)", settings.NVIDIA_STRONG_MODEL, settings.NVIDIA_CHEAP_MODEL)
    else:
        logger.warning("NVIDIA provider: NOT configured (no API key)")

    if not settings.FERNET_KEY:
        logger.warning("FERNET_KEY not set — password encryption disabled")

    logger.info("Default LLM provider: %s", settings.DEFAULT_PROVIDER)
    logger.info("Backend ready on port %d", settings.BACKEND_PORT)

    start_scheduler()

    yield

    stop_scheduler()
    logger.info("Shutting down Job Search Agent backend...")


# ─── App ─────────────────────────────────────────────────────

app = FastAPI(
    title="Job Search Agent",
    description="AI-powered job search and auto-apply agent",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        f"http://localhost:{settings.FRONTEND_PORT}",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routes ──────────────────────────────────────────────────

app.include_router(health_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(profiles_router, prefix="/api")
app.include_router(resumes_router, prefix="/api")
app.include_router(jobs_router, prefix="/api")
app.include_router(matching_router, prefix="/api")
app.include_router(applications_router, prefix="/api")
app.include_router(answer_bank_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(events_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": "Job Search Agent",
        "version": "0.1.0",
        "docs": "/docs",
    }

