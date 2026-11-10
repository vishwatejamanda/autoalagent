"""Resume tailoring service: generates ATS-safe tailored resumes and cover letters."""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel

from sqlmodel import Session, select
from models.application import Resume
from models.profile import MasterProfile, Profile
from models.job import Job
from schemas.profile import MasterProfileData
from services.fact_check import verify_against_master_profile, compute_ats_keyword_coverage
from docs.builder_docx import create_resume_docx
from docs.builder_pdf import create_resume_pdf
from llm.provider import LLMMessage
from llm.router import get_router

logger = logging.getLogger(__name__)


class TailoredContent(BaseModel):
    tailored_summary: str
    tailored_bullets: dict[str, list[str]] = {}  # key: "Company_Title" -> list of bullets
    emphasized_skills: list[str] = []
    missing_skills_gaps: list[str] = []
    cover_letter: str = ""


async def tailor_resume_for_job(
    session: Session,
    job: Job,
    profile: Profile,
    master: MasterProfile,
) -> Resume:
    """Generate or retrieve a tailored resume for a specific job and profile.
    
    Caches results: same job_id + profile_id + master version returns existing resume.
    """
    # 1. Check cache
    cached = session.exec(
        select(Resume)
        .where(Resume.job_id == job.id)
        .where(Resume.profile_id == profile.id)
        .where(Resume.version == master.version)
    ).first()

    if cached and os.path.exists(cached.file_path) and os.path.exists(cached.pdf_path):
        logger.info("Returning cached tailored resume for Job #%d, Profile #%d", job.id, profile.id)
        return cached

    # 2. Parse MasterProfile data
    try:
        master_data = MasterProfileData.model_validate_json(master.data)
    except Exception:
        master_data = MasterProfileData()

    # 3. LLM Generation
    system_prompt = (
        "You are a world-class executive resume writer and ATS specialist.\n"
        "Your goal is to tailor the candidate's resume to match the target Job Description.\n\n"
        "HARD RULES (STRICT):\n"
        "1. Never invent or hallucinate employers, dates, titles, degrees, or skills.\n"
        "2. Reorder, rephrase, and emphasize existing factual achievements to highlight relevant keywords.\n"
        "3. If the JD requires a skill the candidate does NOT have, list it strictly under 'missing_skills_gaps'. NEVER add it to skills.\n"
        "4. Create a concise, tailored professional summary (3-4 sentences).\n"
        "5. Draft a concise 3-paragraph cover letter addressing the hiring team."
    )

    exp_summary = [
        {"key": f"{e.company}_{e.title}", "company": e.company, "title": e.title, "bullets": e.bullets}
        for e in master_data.experience
    ]

    user_prompt = (
        f"--- TARGET JOB DESCRIPTION ---\n"
        f"Title: {job.title}\n"
        f"Company: {job.company}\n"
        f"Description:\n{job.description[:4000]}\n\n"
        f"--- CANDIDATE MASTER PROFILE ---\n"
        f"Name: {master_data.contact.full_name}\n"
        f"Summary: {master_data.summary}\n"
        f"Verified Skills: {json.dumps(master_data.skills)}\n"
        f"Experience: {json.dumps(exp_summary)}\n"
        f"Persona Emphasis: {profile.base_resume_emphasis}"
    )

    tailored: Optional[TailoredContent] = None
    try:
        router = get_router()
        tailored, _ = await router.chat_json(
            messages=[
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(role="user", content=user_prompt),
            ],
            response_model=TailoredContent,
            task="strong",
            temperature=0.2,
            max_retries=2,
        )
    except Exception as exc:
        logger.warning("LLM tailoring failed (%s); using heuristic tailoring fallback", exc)
        score, matched, _ = compute_ats_keyword_coverage(job.description, master_data.skills)
        tailored = TailoredContent(
            tailored_summary=master_data.summary,
            tailored_bullets={f"{e.company}_{e.title}": e.bullets for e in master_data.experience},
            emphasized_skills=master_data.skills,
            missing_skills_gaps=[],
            cover_letter="",
        )

    # 4. Fact-check pass (2nd LLM verification)
    fact_report = await verify_against_master_profile(
        master=master_data,
        tailored_summary=tailored.tailored_summary,
        tailored_bullets=tailored.tailored_bullets,
        tailored_skills=tailored.emphasized_skills or master_data.skills,
        job_description=job.description,
    )

    # Compute final ATS score
    ats_score = fact_report.ats_score
    if ats_score == 0:
        ats_score, _, _ = compute_ats_keyword_coverage(job.description, master_data.skills)

    # 5. Output File Paths
    os.makedirs("./data/resumes", exist_ok=True)
    safe_company = "".join(c for c in job.company if c.isalnum() or c in (" ", "_")).rstrip()
    safe_title = "".join(c for c in job.title if c.isalnum() or c in (" ", "_")).rstrip()
    base_filename = f"Resume_{job.id}_{safe_company[:15]}_{safe_title[:15]}_v{master.version}"
    docx_path = f"./data/resumes/{base_filename}.docx"
    pdf_path = f"./data/resumes/{base_filename}.pdf"

    # Build DOCX and PDF
    create_resume_docx(
        data=master_data,
        output_path=docx_path,
        custom_summary=tailored.tailored_summary,
        tailored_bullets=tailored.tailored_bullets,
    )
    create_resume_pdf(
        data=master_data,
        output_path=pdf_path,
        custom_summary=tailored.tailored_summary,
        tailored_bullets=tailored.tailored_bullets,
    )

    # 6. Save Resume in DB
    resume_record = Resume(
        job_id=job.id,
        profile_id=profile.id or 1,
        version=master.version,
        file_path=docx_path,
        pdf_path=pdf_path,
        ats_score=ats_score,
        is_base=False,
        tailoring_notes=json.dumps({
            "tailored_summary": tailored.tailored_summary,
            "tailored_bullets": tailored.tailored_bullets,
            "emphasized_skills": tailored.emphasized_skills or master_data.skills,
            "cover_letter": tailored.cover_letter,
            "missing_skills": tailored.missing_skills_gaps,
            "fact_check_passed": fact_report.passed,
            "fabrications_detected": fact_report.fabrications_detected,
        }),
        created_at=datetime.now(timezone.utc),
    )
    session.add(resume_record)
    session.commit()
    session.refresh(resume_record)

    return resume_record

