"""Jobs API endpoints: search, scan, filter, Workday company management, and interview prep."""

import json
import logging
import os
from datetime import datetime, timezone
from typing import List, Optional

import yaml
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, or_

from app.database import get_session
from models.job import Job, JobScore
from models.profile import Profile, MasterProfile
from models.audit import AuditLog
from services.dedupe import check_duplicate, compute_description_hash
from sources.workday import WorkdaySource, load_workday_companies
from sources.linkedin import LinkedInSource
from sources.naukri import NaukriSource
from services.interview_prep import generate_interview_prep, generate_company_research
from api.settings_api import load_application_defaults

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
async def list_jobs(
    source: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    role: Optional[str] = None,
    country: Optional[str] = None,
    cities: Optional[str] = None,  # comma-separated string e.g. "San Francisco, San Jose, New York"
    min_score: Optional[int] = None,
    profile_id: Optional[int] = None,
    limit: int = 200,
    offset: int = 0,
    session: Session = Depends(get_session),
):
    """List discovered jobs with filters by source, status, role, country, and multiple cities."""
    query = select(Job)

    if source:
        query = query.where(Job.source == source)
    if status:
        query = query.where(Job.status == status)
    if role:
        query = query.where(Job.title.ilike(f"%{role}%"))
    if country:
        query = query.where(Job.location.ilike(f"%{country}%"))
    if cities:
        city_list = [c.strip() for c in cities.split(",") if c.strip()]
        if city_list:
            city_filters = [Job.location.ilike(f"%{c}%") for c in city_list]
            query = query.where(or_(*city_filters))
    if search:
        query = query.where(
            (Job.title.contains(search)) | (Job.company.contains(search)) | (Job.location.contains(search))  # type: ignore
        )

    jobs = session.exec(query.order_by(Job.id.desc()).offset(offset).limit(limit)).all()

    # Join with scores if available
    results = []
    for j in jobs:
        score_rec = None
        if profile_id:
            score_rec = session.exec(
                select(JobScore).where(JobScore.job_id == j.id).where(JobScore.profile_id == profile_id)
            ).first()
        else:
            score_rec = session.exec(
                select(JobScore).where(JobScore.job_id == j.id).order_by(JobScore.score.desc())
            ).first()

        score_val = score_rec.score if score_rec else 0
        if min_score is not None and score_val < min_score:
            continue

        reasons = []
        gaps = []
        if score_rec:
            try:
                reasons = json.loads(score_rec.reasons or "[]")
                gaps = json.loads(score_rec.gaps or "[]")
            except Exception:
                pass

        results.append({
            "id": j.id,
            "source": j.source,
            "external_id": j.external_id,
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "url": j.url,
            "description": j.description[:300] + ("..." if len(j.description) > 300 else ""),
            "easy_apply": j.easy_apply,
            "status": j.status,
            "score": score_val,
            "reasons": reasons,
            "gaps": gaps,
            "created_at": j.created_at,
        })

    return results


@router.get("/{job_id}")
async def get_job_detail(job_id: int, session: Session = Depends(get_session)):
    """Get full details of a specific job."""
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.description or len(job.description) < 150:
        if job.source == "workday":
            try:
                job = await WorkdaySource().fetch_details(job)
                session.add(job)
                session.commit()
                session.refresh(job)
            except Exception as exc:
                logger.debug("Failed auto-hydrating workday job: %s", exc)

    scores = session.exec(select(JobScore).where(JobScore.job_id == job_id)).all()
    score_list = []
    for s in scores:
        try:
            reasons = json.loads(s.reasons or "[]")
            gaps = json.loads(s.gaps or "[]")
        except Exception:
            reasons, gaps = [], []
        score_list.append({
            "profile_id": s.profile_id,
            "score": s.score,
            "reasons": reasons,
            "gaps": gaps,
        })

    return {
        "id": job.id,
        "source": job.source,
        "external_id": job.external_id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "url": job.url,
        "description": job.description,
        "salary_info": job.salary_info,
        "experience_required": job.experience_required,
        "easy_apply": job.easy_apply,
        "status": job.status,
        "scores": score_list,
        "created_at": job.created_at,
    }


@router.post("/{job_id}/interview-prep")
async def get_job_interview_prep(
    job_id: int,
    body: dict = {},
    session: Session = Depends(get_session),
):
    """Generate interview questions and talking points strictly grounded in candidate facts."""
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    profile_id = body.get("profile_id")
    mp = session.exec(select(MasterProfile).order_by(MasterProfile.id.desc())).first()
    mp_data = json.loads(mp.data) if mp and mp.data else {}

    try:
        prep = await generate_interview_prep(
            job_title=job.title,
            company=job.company,
            job_description=job.description or f"{job.title} at {job.company}",
            master_profile_json=mp_data,
            app_defaults=load_application_defaults(session),
        )
        return prep.model_dump()
    except Exception as exc:
        logger.error("Interview prep error for job %d: %s", job_id, exc)
        raise HTTPException(status_code=500, detail=f"Interview prep generation failed: {exc}")


@router.post("/{job_id}/company-research")
async def get_job_company_research(
    job_id: int,
    session: Session = Depends(get_session),
):
    """Generate company research notes strictly from the job description text."""
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        research = await generate_company_research(
            job_title=job.title,
            company=job.company,
            job_description=job.description or f"{job.title} at {job.company}",
        )
        return research.model_dump()
    except Exception as exc:
        logger.error("Company research error for job %d: %s", job_id, exc)
        raise HTTPException(status_code=500, detail=f"Company research generation failed: {exc}")


@router.post("/scan")
async def trigger_scan(
    body: dict = {},
    session: Session = Depends(get_session),
):
    """Scan allowed portals for a profile and save deduplicated jobs.
    
    Accepts filter overrides in body:
    - roles: list or comma-separated string (e.g. "Software Engineer, AI Engineer")
    - country: string (e.g. "India" or "United States")
    - cities: list or comma-separated string (e.g. "Bengaluru, Hyderabad, Remote")
    - portals: list of portals to scan (e.g. ["workday", "linkedin", "naukri"])
    - limit: max jobs per portal (default: 20)
    - profile_id: ID of the Profile persona to use as base defaults
    """
    profile_id = body.get("profile_id")
    profile = session.get(Profile, profile_id) if profile_id else session.exec(select(Profile)).first()
    if not profile:
        profile = Profile(name="Default Profile", target_titles='["Software Engineer"]', id=1)

    # Resolve scan portals: prioritize request body over profile settings
    if body.get("portals") and isinstance(body["portals"], list) and len(body["portals"]) > 0:
        allowed_portals = [p.lower().strip() for p in body["portals"] if p.strip()]
    else:
        allowed_portals = json.loads(profile.allowed_portals or '["workday"]')

    # Compile filter overrides
    scan_filters = {
        "roles": body.get("roles") or body.get("role"),
        "country": body.get("country"),
        "cities": body.get("cities"),
        "limit": body.get("limit", 40),
    }

    new_jobs_added = 0
    duplicates_skipped = 0

    # 1. Workday scan (fast REST CXS)
    if "workday" in allowed_portals:
        try:
            adapter = WorkdaySource()
            found = await adapter.search(profile, filters=scan_filters)
            for j in found:
                is_dup, _ = check_duplicate(session, j)
                if not is_dup:
                    session.add(j)
                    new_jobs_added += 1
                else:
                    duplicates_skipped += 1
            session.commit()
        except Exception as exc:
            logger.error("Error during Workday scan: %s", exc)

    # 2. LinkedIn scan (if allowed)
    if "linkedin" in allowed_portals:
        try:
            adapter = LinkedInSource()
            found = await adapter.search(profile, filters=scan_filters)
            for j in found:
                is_dup, _ = check_duplicate(session, j)
                if not is_dup:
                    session.add(j)
                    new_jobs_added += 1
                else:
                    duplicates_skipped += 1
            session.commit()
        except Exception as exc:
            logger.error("Error during LinkedIn scan: %s", exc)

    # 3. Naukri scan (if allowed)
    if "naukri" in allowed_portals:
        try:
            adapter = NaukriSource()
            found = await adapter.search(profile, filters=scan_filters)
            for j in found:
                is_dup, _ = check_duplicate(session, j)
                if not is_dup:
                    session.add(j)
                    new_jobs_added += 1
                else:
                    duplicates_skipped += 1
            session.commit()
        except Exception as exc:
            logger.error("Error during Naukri scan: %s", exc)

    session.add(AuditLog(
        action="job_scan_completed",
        entity_type="job",
        details=f"Scan completed. Portals: {allowed_portals}. Added {new_jobs_added} jobs, skipped {duplicates_skipped} duplicates.",
        created_at=datetime.now(timezone.utc),
    ))
    session.commit()

    return {
        "success": True,
        "portals_scanned": allowed_portals,
        "filters_applied": {k: v for k, v in scan_filters.items() if v},
        "new_jobs_added": new_jobs_added,
        "duplicates_skipped": duplicates_skipped,
        "profile_id": profile.id,
    }


# ─── Workday Company Management ──────────────────────────────


@router.get("/workday/companies")
async def get_workday_companies():
    """List all configured Workday tenant career sites."""
    return load_workday_companies()


@router.post("/workday/companies")
async def add_workday_company(body: dict):
    """Add a new Workday company tenant to workday_companies.yaml."""
    name = body.get("name")
    tenant = body.get("tenant")
    site = body.get("site")
    base_url = body.get("base_url")

    if not tenant or not site:
        raise HTTPException(status_code=400, detail="tenant and site are required")

    yaml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sources", "workday_companies.yaml")
    companies = load_workday_companies()

    # Check if tenant already exists
    if any(c.get("tenant") == tenant for c in companies):
        raise HTTPException(status_code=400, detail="Company tenant already configured")

    new_company = {
        "name": name or tenant.capitalize(),
        "tenant": tenant,
        "site": site,
        "base_url": base_url or f"https://{tenant}.wd5.myworkdayjobs.com/{site}",
    }
    companies.append(new_company)

    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump({"companies": companies}, f)

    return new_company


@router.delete("/workday/companies/{tenant}")
async def remove_workday_company(tenant: str):
    """Remove a Workday company tenant."""
    yaml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sources", "workday_companies.yaml")
    companies = load_workday_companies()

    filtered = [c for c in companies if c.get("tenant") != tenant]
    if len(filtered) == len(companies):
        raise HTTPException(status_code=404, detail="Company tenant not found")

    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump({"companies": filtered}, f)

    return {"deleted": tenant}
