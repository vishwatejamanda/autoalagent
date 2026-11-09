"""Job Matching & Review Queue API endpoints."""

import json
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from models.job import Job, JobScore
from models.profile import Profile, MasterProfile
from models.audit import AuditLog
from schemas.profile import MasterProfileData
from services.matcher import score_job_for_profile

router = APIRouter(prefix="/matching", tags=["matching"])


@router.post("/score-all")
async def score_unscored_jobs(
    body: dict = {},
    session: Session = Depends(get_session),
):
    """Score all unscored jobs for a specific profile."""
    profile_id = body.get("profile_id")
    profile = session.get(Profile, profile_id) if profile_id else session.exec(select(Profile)).first()
    if not profile:
        profile = Profile(name="Default Profile", id=1)

    master = session.exec(select(MasterProfile).order_by(MasterProfile.id.desc())).first()
    master_data = MasterProfileData()
    if master:
        try:
            master_data = MasterProfileData.model_validate_json(master.data)
        except Exception:
            pass

    unscored_jobs = session.exec(
        select(Job).where(Job.status.in_(["new", "matched"])).order_by(Job.id.desc()).limit(50)  # type: ignore
    ).all()

    scored_count = 0
    matched_count = 0

    for job in unscored_jobs:
        score_rec = await score_job_for_profile(session, job, profile, master_data)
        scored_count += 1
        if score_rec.score >= profile.min_match_score:
            matched_count += 1

    session.add(AuditLog(
        action="batch_matching_completed",
        entity_type="matching",
        details=f"Scored {scored_count} jobs. {matched_count} met threshold ({profile.min_match_score}).",
        created_at=datetime.now(timezone.utc),
    ))
    session.commit()

    return {
        "success": True,
        "scored_count": scored_count,
        "matched_count": matched_count,
        "min_score_threshold": profile.min_match_score,
    }


@router.get("/review-queue")
async def get_review_queue(
    profile_id: Optional[int] = None,
    session: Session = Depends(get_session),
):
    """Retrieve jobs in the Review Queue awaiting user confirmation."""
    profile = session.get(Profile, profile_id) if profile_id else session.exec(select(Profile)).first()
    min_score = profile.min_match_score if profile else 60

    # Find jobs matched with score >= min_score
    query = (
        select(Job, JobScore)
        .join(JobScore, Job.id == JobScore.job_id)
        .where(JobScore.score >= min_score)
        .where(Job.status.in_(["new", "matched"]))  # type: ignore
        .order_by(JobScore.score.desc())  # type: ignore
    )
    items = session.exec(query).all()

    results = []
    for job, score_rec in items:
        reasons, gaps, red_flags = [], [], []
        try:
            reasons = json.loads(score_rec.reasons or "[]")
            gaps = json.loads(score_rec.gaps or "[]")
            red_flags = json.loads(score_rec.red_flags or "[]")
        except Exception:
            pass

        results.append({
            "job_id": job.id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "url": job.url,
            "source": job.source,
            "easy_apply": job.easy_apply,
            "score": score_rec.score,
            "reasons": reasons,
            "gaps": gaps,
            "red_flags": red_flags,
            "status": job.status,
            "created_at": job.created_at,
        })

    return results


@router.post("/review-queue/{job_id}/action")
async def review_queue_action(
    job_id: int,
    body: dict,
    session: Session = Depends(get_session),
):
    """Perform action on review queue item: 'approve', 'reject', or 'manual'."""
    action = body.get("action")
    if action not in ("approve", "reject", "manual"):
        raise HTTPException(status_code=400, detail="Action must be 'approve', 'reject', or 'manual'")

    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if action == "approve":
        job.status = "approved"
    elif action == "reject":
        job.status = "rejected"
    elif action == "manual":
        job.status = "manual"

    session.add(job)
    session.add(AuditLog(
        action=f"review_queue_{action}",
        entity_type="job",
        entity_id=job.id,
        details=f"Job '{job.title}' at {job.company} moved to '{job.status}'",
        created_at=datetime.now(timezone.utc),
    ))
    session.commit()

    return {"job_id": job.id, "new_status": job.status}

