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
from docs.builder_latex import (
    render_tailored_latex,
    render_latex_styled_pdf,
    try_compile_latex_to_pdf,
)
from llm.skills.resume_tailor_skill import TailoredResumeOutput, skill_tailor_resume

logger = logging.getLogger(__name__)


class TailoredContent(TailoredResumeOutput):
    pass


async def tailor_resume_for_job(
    session: Session,
    job: Job,
    profile: Profile,
    master: MasterProfile,
    app_defaults: Optional[dict] = None,
    force_regenerate: bool = False,
) -> Resume:
    """Generate or retrieve a tailored resume for a specific job and profile.
    
    Uses Nemotron AI tailoring skill + LaTeX builder + LaTeX-styled A4 PDF rendering.
    """
    # 1. Check cache
    cached = session.exec(
        select(Resume)
        .where(Resume.job_id == job.id)
        .where(Resume.profile_id == profile.id)
        .where(Resume.version == master.version)
    ).first()

    if cached and not force_regenerate and os.path.exists(cached.file_path) and os.path.exists(cached.pdf_path):
        try:
            notes_data = json.loads(cached.tailoring_notes or "{}")
            if notes_data.get("latex_source") and notes_data.get("latex_pdf_rendered"):
                logger.info("Returning cached tailored resume for Job #%d, Profile #%d", job.id, profile.id)
                return cached
        except Exception:
            pass

    # 2. Parse MasterProfile data
    try:
        master_data = MasterProfileData.model_validate_json(master.data)
    except Exception:
        master_data = MasterProfileData()

    # 3. Modular Context-Efficient AI Tailoring Skill (Nemotron)
    tailored: Optional[TailoredResumeOutput] = None
    try:
        tailored = await skill_tailor_resume(
            master=master_data,
            job_title=job.title,
            company=job.company,
            job_description=job.description,
            profile=profile,
            app_defaults=app_defaults,
        )
    except Exception as exc:
        logger.warning("LLM tailoring skill failed (%s); using heuristic tailoring fallback", exc)
        tailored = TailoredResumeOutput(
            tailored_summary=master_data.summary,
            tailored_bullets={f"{e.company}_{e.title}": e.bullets for e in master_data.experience},
            tailored_project_bullets={p.name: p.bullets for p in master_data.projects},
            recommended_project_order=[p.name for p in master_data.projects],
            emphasized_skills=master_data.skills,
            tailored_interests=getattr(master_data, "areas_of_interest", []),
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
    tex_path = f"./data/resumes/{base_filename}.tex"

    # Build LaTeX (.tex), compile via pdflatex or LaTeX-identical Chromium PDF (fallback ReportLab) + DOCX
    _, rendered_latex = render_tailored_latex(
        data=master_data,
        output_path=tex_path,
        custom_summary=tailored.tailored_summary,
        tailored_bullets=tailored.tailored_bullets,
        tailored_project_bullets=tailored.tailored_project_bullets,
        emphasized_skills=tailored.emphasized_skills or master_data.skills,
        tailored_interests=tailored.tailored_interests or getattr(master_data, "areas_of_interest", []),
        project_order=tailored.recommended_project_order,
    )
    compiled_from_latex = try_compile_latex_to_pdf(tex_path, pdf_path)
    latex_pdf_rendered = compiled_from_latex
    if not compiled_from_latex:
        latex_pdf_rendered = await render_latex_styled_pdf(
            data=master_data,
            pdf_output_path=pdf_path,
            custom_summary=tailored.tailored_summary,
            tailored_bullets=tailored.tailored_bullets,
            tailored_project_bullets=tailored.tailored_project_bullets,
            emphasized_skills=tailored.emphasized_skills or master_data.skills,
            tailored_interests=tailored.tailored_interests or getattr(master_data, "areas_of_interest", []),
            project_order=tailored.recommended_project_order,
        )
    if not latex_pdf_rendered:
        create_resume_pdf(
            data=master_data,
            output_path=pdf_path,
            custom_summary=tailored.tailored_summary,
            tailored_bullets=tailored.tailored_bullets,
        )

    create_resume_docx(
        data=master_data,
        output_path=docx_path,
        custom_summary=tailored.tailored_summary,
        tailored_bullets=tailored.tailored_bullets,
    )

    # 6. Save Resume in DB
    notes_payload = {
        "tailored_summary": tailored.tailored_summary,
        "tailored_bullets": tailored.tailored_bullets,
        "tailored_project_bullets": tailored.tailored_project_bullets,
        "recommended_project_order": tailored.recommended_project_order,
        "tailored_interests": tailored.tailored_interests,
        "emphasized_skills": tailored.emphasized_skills or master_data.skills,
        "cover_letter": tailored.cover_letter,
        "missing_skills": tailored.missing_skills_gaps,
        "fact_check_passed": fact_report.passed,
        "fabrications_detected": fact_report.fabrications_detected,
        "tex_path": tex_path,
        "latex_compiled_pdf": compiled_from_latex,
        "latex_pdf_rendered": latex_pdf_rendered,
        "latex_source": rendered_latex,
    }

    if cached:
        cached.file_path = docx_path
        cached.pdf_path = pdf_path
        cached.ats_score = ats_score
        cached.tailoring_notes = json.dumps(notes_payload)
        cached.created_at = datetime.now(timezone.utc)
        session.add(cached)
        session.commit()
        session.refresh(cached)
        return cached

    resume_record = Resume(
        job_id=job.id,
        profile_id=profile.id or 1,
        version=master.version,
        file_path=docx_path,
        pdf_path=pdf_path,
        ats_score=ats_score,
        is_base=False,
        tailoring_notes=json.dumps(notes_payload),
        created_at=datetime.now(timezone.utc),
    )
    session.add(resume_record)
    session.commit()
    session.refresh(resume_record)

    return resume_record

