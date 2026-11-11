"""Resumes & Tailoring API endpoints."""

import json
import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from sqlmodel import Session, select

from app.database import get_session
from models.application import Resume
from models.profile import MasterProfile, Profile
from models.job import Job
from schemas.profile import MasterProfileData
from services.resume_tailor import tailor_resume_for_job
from api.settings_api import load_application_defaults

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

    resume = await tailor_resume_for_job(
        session,
        job,
        profile,
        master,
        app_defaults=load_application_defaults(session),
        force_regenerate=bool(body.get("force", False)),
    )

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
        "tex_path": notes.get("tex_path", ""),
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

    tex_path = notes.get("tex_path") or (resume.pdf_path[:-4] + ".tex" if resume.pdf_path.endswith(".pdf") else "")
    return {
        "id": resume.id,
        "job_id": resume.job_id,
        "profile_id": resume.profile_id,
        "version": resume.version,
        "ats_score": resume.ats_score,
        "tailoring_notes": notes,
        "docx_available": os.path.exists(resume.file_path),
        "pdf_available": os.path.exists(resume.pdf_path),
        "tex_available": bool(notes.get("latex_source") or (tex_path and os.path.exists(tex_path))),
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
        "emphasized_skills": notes.get("emphasized_skills", master_data.skills),
        "base_experience": [
            {"company": e.company, "title": e.title, "bullets": e.bullets}
            for e in master_data.experience
        ],
        "tailored_bullets": notes.get("tailored_bullets", {}),
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


@router.get("/{resume_id}/download/tex")
async def download_tex(resume_id: int, session: Session = Depends(get_session)):
    """Download the tailored resume LaTeX (.tex) source."""
    resume = session.get(Resume, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    notes = {}
    try:
        notes = json.loads(resume.tailoring_notes or "{}")
    except Exception:
        pass
    tex_path = notes.get("tex_path") or (resume.pdf_path[:-4] + ".tex" if resume.pdf_path.endswith(".pdf") else "")
    if tex_path and os.path.exists(tex_path):
        return FileResponse(
            tex_path,
            media_type="application/x-tex",
            filename=os.path.basename(tex_path),
        )
    if notes.get("latex_source"):
        return PlainTextResponse(
            notes["latex_source"],
            media_type="application/x-tex",
            headers={"Content-Disposition": f'attachment; filename="Resume_{resume.id}.tex"'},
        )
    raise HTTPException(status_code=404, detail="LaTeX (.tex) source not found for this resume")


@router.get("/{resume_id}/latex")
async def get_resume_latex(resume_id: int, session: Session = Depends(get_session)):
    """Return raw tailored LaTeX code for preview/copying."""
    resume = session.get(Resume, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    notes = {}
    try:
        notes = json.loads(resume.tailoring_notes or "{}")
    except Exception:
        pass
    latex_code = notes.get("latex_source", "")
    if not latex_code:
        tex_path = notes.get("tex_path") or (resume.pdf_path[:-4] + ".tex" if resume.pdf_path.endswith(".pdf") else "")
        if tex_path and os.path.exists(tex_path):
            with open(tex_path, "r", encoding="utf-8") as f:
                latex_code = f.read()
    if not latex_code:
        raise HTTPException(status_code=404, detail="LaTeX source not available")
    return {"resume_id": resume.id, "latex": latex_code}

