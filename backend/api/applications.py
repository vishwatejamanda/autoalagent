"""Applications Engine, Manual Queue, and Kanban Tracker API."""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from models.application import Application, Resume
from models.job import Job
from models.profile import Profile, MasterProfile
from models.audit import AuditLog
from schemas.profile import MasterProfileData
from services.resume_tailor import tailor_resume_for_job
from appliers.linkedin import LinkedInApplier
from appliers.naukri import NaukriApplier
from appliers.workday import WorkdayApplier

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/applications", tags=["applications"])

_KILL_SWITCH_ACTIVE = False


@router.post("/kill-switch")
async def toggle_kill_switch(body: dict = {}):
    """Emergency global stop switch for all background application bots."""
    global _KILL_SWITCH_ACTIVE
    action = body.get("active")
    if action is not None:
        _KILL_SWITCH_ACTIVE = bool(action)
    else:
        _KILL_SWITCH_ACTIVE = not _KILL_SWITCH_ACTIVE

    return {
        "kill_switch_active": _KILL_SWITCH_ACTIVE,
        "message": "EMERGENCY STOP ENGAGED" if _KILL_SWITCH_ACTIVE else "Automation resumed",
    }


@router.get("/kill-switch")
async def get_kill_switch_status():
    """Check if emergency kill switch is currently active."""
    return {"kill_switch_active": _KILL_SWITCH_ACTIVE}


@router.post("/apply")
async def apply_to_job(
    body: dict,
    session: Session = Depends(get_session),
):
    """Trigger application for a job using the appropriate portal applier."""
    global _KILL_SWITCH_ACTIVE
    if _KILL_SWITCH_ACTIVE:
        raise HTTPException(status_code=400, detail="Kill switch is active. Automated applications are paused.")

    job_id = body.get("job_id")
    profile_id = body.get("profile_id")
    mode_override = body.get("mode")  # "review" | "auto"

    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    profile = session.get(Profile, profile_id) if profile_id else session.exec(select(Profile)).first()
    if not profile:
        profile = Profile(name="Default Profile", id=1)

    master = session.exec(select(MasterProfile).order_by(MasterProfile.id.desc())).first()
    if not master:
        raise HTTPException(status_code=400, detail="Master profile required before applying")

    try:
        master_data = MasterProfileData.model_validate_json(master.data)
    except Exception:
        master_data = MasterProfileData()

    # Step 1: Ensure tailored resume exists
    resume = await tailor_resume_for_job(session, job, profile, master)
    resume_file = resume.pdf_path if os.path.exists(resume.pdf_path) else resume.file_path

    mode = mode_override or profile.auto_apply_mode or "review"
    if mode == "off":
        return {"status": "off", "message": "Profile auto_apply_mode is set to 'off'."}

    # Step 2: Route to appropriate portal applier
    applier = None
    if job.source == "linkedin":
        applier = LinkedInApplier(session, master_data)
    elif job.source == "naukri":
        applier = NaukriApplier(session, master_data)
    elif job.source == "workday":
        applier = WorkdayApplier(session, master_data)

    if not applier:
        # Move to manual queue
        job.status = "manual"
        session.add(job)
        session.commit()
        return {
            "status": "manual_needed",
            "message": f"Source '{job.source}' requires manual application on company site.",
            "job_url": job.url,
            "resume_id": resume.id,
        }

    # Execute application flow
    result = await applier.apply(job=job, resume_path=resume_file, mode=mode)

    # Record Application row
    app_record = Application(
        job_id=job.id,
        profile_id=profile.id or 1,
        resume_id=resume.id,
        status="submitted" if result.status == "submitted" else "pending",
        mode=mode,
        applied_at=datetime.now(timezone.utc) if result.status == "submitted" else None,
        portal=job.source,
        screenshot_path=result.screenshot_path,
        error_message=result.error_message,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(app_record)

    if result.status == "submitted":
        job.status = "applied"
    elif result.status == "manual_needed":
        job.status = "manual"
    elif result.status == "review_needed":
        job.status = "review"

    session.add(job)
    session.add(AuditLog(
        action=f"application_{result.status}",
        entity_type="application",
        entity_id=job.id,
        details=f"Job '{job.title}' ({job.company}): {result.details or result.error_message}",
        created_at=datetime.now(timezone.utc),
    ))
    session.commit()
    session.refresh(app_record)

    return {
        "application_id": app_record.id,
        "job_id": job.id,
        "status": result.status,
        "details": result.details,
        "screenshot": result.screenshot_path,
        "error": result.error_message,
    }


@router.get("/tracker")
async def get_applications_tracker(session: Session = Depends(get_session)):
    """Kanban Tracker: list jobs grouped by application stages."""
    jobs = session.exec(select(Job).order_by(Job.id.desc())).all()

    stages = {
        "found": [],
        "matched": [],
        "applied": [],
        "responded": [],
        "interview": [],
        "offer": [],
        "rejected": [],
    }

    for j in jobs:
        st = j.status
        if st in ("new", ""):
            stage_key = "found"
        elif st in ("matched", "approved", "review"):
            stage_key = "matched"
        elif st == "applied":
            stage_key = "applied"
        elif st in stages:
            stage_key = st
        else:
            stage_key = "found"

        stages[stage_key].append({
            "id": j.id,
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "source": j.source,
            "url": j.url,
            "status": j.status,
            "created_at": j.created_at,
        })

    return stages


@router.put("/tracker/{job_id}")
async def update_tracker_stage(job_id: int, body: dict, session: Session = Depends(get_session)):
    """Move job to a new Kanban stage (e.g. responded, interview, offer, rejected)."""
    new_status = body.get("status")
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = new_status
    session.add(job)
    session.add(AuditLog(
        action="tracker_stage_moved",
        entity_type="job",
        entity_id=job.id,
        details=f"Moved job #{job.id} to '{new_status}'",
        created_at=datetime.now(timezone.utc),
    ))
    session.commit()
    return {"job_id": job.id, "new_status": job.status}


@router.get("/manual-queue")
async def get_manual_queue(session: Session = Depends(get_session)):
    """Fetch jobs requiring manual application with ready-to-download tailored resumes."""
    jobs = session.exec(select(Job).where(Job.status == "manual").order_by(Job.id.desc())).all()
    results = []
    for j in jobs:
        resume = session.exec(
            select(Resume).where(Resume.job_id == j.id).order_by(Resume.id.desc())
        ).first()

        results.append({
            "id": j.id,
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "source": j.source,
            "url": j.url,
            "resume_id": resume.id if resume else None,
            "docx_path": resume.file_path if resume else None,
            "pdf_path": resume.pdf_path if resume else None,
            "ats_score": resume.ats_score if resume else None,
        })
    return results
