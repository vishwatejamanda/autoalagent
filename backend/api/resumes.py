"""Resumes & Tailoring API endpoints."""

import json
import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from app.database import get_session
from models.application import Resume
from models.profile import MasterProfile, Profile
from models.job import Job
from schemas.profile import MasterProfileData
from services.resume_tailor import tailor_resume_for_job

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("/tailor")
async def trigger_tailor_resume(
    body: dict,
    session: Session = Depends(get_session),
):
    """Generate or retrieve a tailored resume for a job and profile."""
    job_id = body.get("job_id")
    profile_id = body.get("profile_id")

    if not job_id:
        raise HTTPException(status_code=400, detail="job_id is required")

    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    profile = session.get(Profile, profile_id) if profile_id else session.exec(select(Profile)).first()
    if not profile:
        # Default placeholder profile if none exists
        profile = Profile(name="Default Profile", id=1)

    master = session.exec(select(MasterProfile).order_by(MasterProfile.id.desc())).first()
    if not master:
        raise HTTPException(status_code=400, detail="Master Profile is empty. Please upload or create a Master Profile first.")

    resume = await tailor_resume_for_job(session, job, profile, master)

    notes = {}
    try:
        notes = json.loads(resume.tailoring_notes or "{}")
    except Exception:
        pass

    return {
        "id": resume.id,
        "job_id": resume.job_id,
        "profile_id": resume.profile_id,
        "version": resume.version,
        "ats_score": resume.ats_score,
        "file_path": resume.file_path,
        "pdf_path": resume.pdf_path,
        "tailoring_notes": notes,
        "created_at": resume.created_at,
    }


@router.get("/job/{job_id}")
async def get_resume_for_job(job_id: int, session: Session = Depends(get_session)):
    """Fetch the latest tailored resume generated for a job."""
    resume = session.exec(
        select(Resume).where(Resume.job_id == job_id).order_by(Resume.id.desc())
    ).first()
    if not resume:
        raise HTTPException(status_code=404, detail="No tailored resume found for this job")

    notes = {}
    try:
        notes = json.loads(resume.tailoring_notes or "{}")
    except Exception:
        pass

    return {
        "id": resume.id,
        "job_id": resume.job_id,
        "profile_id": resume.profile_id,
        "version": resume.version,
        "ats_score": resume.ats_score,
        "tailoring_notes": notes,
        "docx_available": os.path.exists(resume.file_path),
        "pdf_available": os.path.exists(resume.pdf_path),
        "created_at": resume.created_at,
    }


@router.get("/{resume_id}/diff")
async def get_resume_diff(resume_id: int, session: Session = Depends(get_session)):
    """Get side-by-side diff between Master Profile and tailored resume."""
    resume = session.get(Resume, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    master = session.exec(select(MasterProfile).order_by(MasterProfile.id.desc())).first()
    master_data = MasterProfileData()
    if master:
        try:
            master_data = MasterProfileData.model_validate_json(master.data)
        except Exception:
            pass

    notes = {}
    try:
        notes = json.loads(resume.tailoring_notes or "{}")
    except Exception:
        pass

    return {
        "base_summary": master_data.summary,
        "tailored_summary": notes.get("tailored_summary", master_data.summary),
        "base_skills": master_data.skills,
        "cover_letter": notes.get("cover_letter", ""),
        "missing_skills": notes.get("missing_skills", []),
        "ats_score": resume.ats_score,
        "fact_check_passed": notes.get("fact_check_passed", True),
        "fabrications_detected": notes.get("fabrications_detected", []),
    }


@router.get("/{resume_id}/download/docx")
async def download_docx(resume_id: int, session: Session = Depends(get_session)):
    """Download the tailored resume DOCX."""
    resume = session.get(Resume, resume_id)
    if not resume or not os.path.exists(resume.file_path):
        raise HTTPException(status_code=404, detail="DOCX file not found")
    return FileResponse(
        resume.file_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=os.path.basename(resume.file_path),
    )


@router.get("/{resume_id}/download/pdf")
async def download_pdf(resume_id: int, session: Session = Depends(get_session)):
    """Download the tailored resume PDF."""
    resume = session.get(Resume, resume_id)
    if not resume or not os.path.exists(resume.pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found")
    return FileResponse(
        resume.pdf_path,
        media_type="application/pdf",
        filename=os.path.basename(resume.pdf_path),
    )

