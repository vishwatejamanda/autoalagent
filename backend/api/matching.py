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
from services.event_bus import event_bus

router = APIRouter(prefix="/matching", tags=["matching"])


@router.post("/score-all")
async def score_unscored_jobs(
    body: dict = {},
    session: Session = Depends(get_session),
):
    """Score all unscored jobs (or rescore all if force_rescore=True) for a specific profile."""
    profile_id = body.get("profile_id")
    force_rescore = body.get("force_rescore", False)
    limit = body.get("limit", 50)

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

    query = select(Job).where(Job.status.in_(["new", "matched"])).order_by(Job.id.desc()).limit(limit)  # type: ignore
    unscored_jobs = session.exec(query).all()

    scored_count = 0
    matched_count = 0
    total = len(unscored_jobs)

    await event_bus.publish("matching_started", {
        "total_jobs": total,
        "profile_id": profile.id,
        "profile_name": profile.name,
        "force_rescore": force_rescore,
    })

    for idx, job in enumerate(unscored_jobs):
        score_rec = await score_job_for_profile(
            session=session,
            job=job,
            profile=profile,
            master=master_data,
            force_rescore=force_rescore,
        )
        scored_count += 1
        if score_rec.score >= profile.min_match_score:
            matched_count += 1

        if (idx + 1) % 5 == 0 or (idx + 1) == total:
            await event_bus.publish("matching_progress", {
                "current": idx + 1,
                "total": total,
                "scored_count": scored_count,
                "matched_count": matched_count,
            })

    session.add(AuditLog(
        action="batch_matching_completed",
        entity_type="matching",
        details=f"Scored {scored_count}/{total} jobs for profile '{profile.name}'. {matched_count} met threshold ({profile.min_match_score}).",
        created_at=datetime.now(timezone.utc),
    ))
    session.commit()

    await event_bus.publish("matching_completed", {
        "scored_count": scored_count,
        "matched_count": matched_count,
        "min_score_threshold": profile.min_match_score,
    })

    return {
        "success": True,
        "scored_count": scored_count,
        "matched_count": matched_count,
        "min_score_threshold": profile.min_match_score,
        "profile_name": profile.name,
    }


@router.post("/score/{job_id}")
async def score_single_job(
    job_id: int,
    body: dict = {},
    session: Session = Depends(get_session),
):
    """Score or rescore a single job against a persona profile."""
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

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

    score_rec = await score_job_for_profile(
        session=session,
        job=job,
        profile=profile,
        master=master_data,
        force_rescore=True,
    )

    reasons, gaps, red_flags = [], [], []
    try:
        reasons = json.loads(score_rec.reasons or "[]")
        gaps = json.loads(score_rec.gaps or "[]")
        red_flags = json.loads(score_rec.red_flags or "[]")
    except Exception:
        pass

    session.add(AuditLog(
        action="single_job_scored",
        entity_type="job",
        entity_id=job.id,
        details=f"Job '{job.title}' scored {score_rec.score}/100 for profile '{profile.name}'",
        created_at=datetime.now(timezone.utc),
    ))
    session.commit()

    return {
        "success": True,
        "job_id": job.id,
        "title": job.title,
        "company": job.company,
        "score": score_rec.score,
        "reasons": reasons,
        "gaps": gaps,
        "red_flags": red_flags,
        "status": job.status,
    }


@router.get("/review-queue")
async def get_review_queue(
    profile_id: Optional[int] = None,
    min_score: Optional[int] = None,
    source: Optional[str] = None,
    session: Session = Depends(get_session),
):
    """Retrieve jobs in the Review Queue awaiting user confirmation."""
    profile = session.get(Profile, profile_id) if profile_id else session.exec(select(Profile)).first()
    effective_min_score = min_score if min_score is not None else (profile.min_match_score if profile else 60)

    query = (
        select(Job, JobScore)
        .join(JobScore, Job.id == JobScore.job_id)
        .where(JobScore.score >= effective_min_score)
        .where(Job.status.in_(["new", "matched"]))  # type: ignore
    )

    if profile_id:
        query = query.where(JobScore.profile_id == profile_id)
    if source and source.lower() != "all":
        query = query.where(Job.source == source.lower())

    query = query.order_by(JobScore.score.desc())  # type: ignore
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
            "description_preview": (job.description[:200] + "...") if job.description else "",
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

    await event_bus.publish("review_action_completed", {
        "job_id": job.id,
        "action": action,
        "new_status": job.status,
        "title": job.title,
        "company": job.company,
    })

    return {"job_id": job.id, "new_status": job.status}
