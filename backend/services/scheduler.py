"""APScheduler internal background worker service."""

import logging
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.database import engine
from sqlmodel import Session, select
from models.job import Job
from models.profile import Profile, MasterProfile
from schemas.profile import MasterProfileData
from services.matcher import score_job_for_profile
from services.notifier import notify_new_matches, send_telegram_message

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def scheduled_scoring_job():
    """Background task to score newly discovered jobs."""
    logger.info("Running scheduled job scoring...")
    try:
        with Session(engine) as session:
            profile = session.exec(select(Profile)).first()
            if not profile:
                return

            master = session.exec(select(MasterProfile).order_by(MasterProfile.id.desc())).first()
            master_data = MasterProfileData()
            if master:
                try:
                    master_data = MasterProfileData.model_validate_json(master.data)
                except Exception:
                    pass

            unscored = session.exec(
                select(Job).where(Job.status == "new").order_by(Job.id.desc()).limit(15)
            ).all()

            matched_count = 0
            top_title = ""
            top_company = ""

            for job in unscored:
                score_rec = await score_job_for_profile(session, job, profile, master_data)
                if score_rec.score >= profile.min_match_score:
                    matched_count += 1
                    top_title = job.title
                    top_company = job.company

            if matched_count > 0:
                await notify_new_matches(matched_count, top_title, top_company)
    except Exception as exc:
        logger.error("Error in scheduled scoring job: %s", exc)


def start_scheduler():
    """Initialize and start APScheduler within backend process."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
        # Schedule scoring every 30 minutes
        _scheduler.add_job(
            scheduled_scoring_job,
            trigger=IntervalTrigger(minutes=30),
            id="periodic_scoring",
            replace_existing=True,
        )
        _scheduler.start()
        logger.info("APScheduler initialized and running.")


def stop_scheduler():
    """Shut down APScheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped.")
        _scheduler = None


def get_scheduler_status() -> dict:
    """Return current APScheduler state and scheduled jobs."""
    if not _scheduler or not _scheduler.running:
        return {"running": False, "jobs": []}
    jobs = []
    for j in _scheduler.get_jobs():
        jobs.append({
            "id": j.id,
            "next_run_time": j.next_run_time.isoformat() if j.next_run_time else None,
        })
    return {"running": True, "jobs": jobs}

