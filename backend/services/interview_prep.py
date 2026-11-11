"""Interview preparation and company research note generator using modular AI Skills."""

from __future__ import annotations

from typing import Optional

from llm.router import LLMRouter
from llm.skills.interview_prep_skill import (
    InterviewQuestion,
    InterviewPrepResult,
    CompanyResearchResult,
    skill_prepare_interview,
    skill_company_research,
)
from schemas.profile import MasterProfileData


async def generate_interview_prep(
    job_title: str,
    company: str,
    job_description: str,
    master_profile_json: dict,
    router: Optional[LLMRouter] = None,
    app_defaults: Optional[dict] = None,
) -> InterviewPrepResult:
    """Generate interview prep via modular interview_prep_skill using compact context."""
    try:
        master = MasterProfileData.model_validate(master_profile_json or {})
    except Exception:
        master = MasterProfileData()

    return await skill_prepare_interview(
        master=master,
        job_title=job_title,
        company=company,
        job_description=job_description,
        app_defaults=app_defaults,
        llm_router=router,
    )


async def generate_company_research(
    job_title: str,
    company: str,
    job_description: str,
    router: Optional[LLMRouter] = None,
) -> CompanyResearchResult:
    """Extract company research notes strictly from condensed Job Description text."""
    return await skill_company_research(
        job_title=job_title,
        company=company,
        job_description=job_description,
        llm_router=router,
    )
