"""Resume Tailoring AI Skill (Nemotron-powered Full Resume Rebuilder).

Tailors summary, JD-inclined project & experience bullets, project priority order,
verified skills ordering, areas of interest, and cover letter for a specific Job
Description using a compact context slice.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional
from pydantic import BaseModel, Field

from llm.provider import LLMMessage
from llm.router import LLMRouter, get_router
from llm.skills.context_builder import build_compact_context, extract_salient_jd
from schemas.profile import MasterProfileData

logger = logging.getLogger(__name__)


class TailoredResumeOutput(BaseModel):
    tailored_summary: str
    tailored_bullets: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Keyed by 'Company_Title' for prior employment entries",
    )
    tailored_project_bullets: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Keyed by exact project name; 3-4 JD-inclined bullets per project",
    )
    recommended_project_order: list[str] = Field(
        default_factory=list,
        description="Exact project names ordered by highest relevance to the target JD",
    )
    emphasized_skills: list[str] = Field(default_factory=list)
    tailored_interests: list[str] = Field(default_factory=list)
    missing_skills_gaps: list[str] = Field(default_factory=list)
    cover_letter: str = ""


async def skill_tailor_resume(
    master: MasterProfileData,
    job_title: str,
    company: str,
    job_description: str,
    profile: Optional[Any] = None,
    app_defaults: Optional[dict[str, Any]] = None,
    llm_router: Optional[LLMRouter] = None,
) -> TailoredResumeOutput:
    """Run the modular Resume Tailoring skill on a compact context slice using Nemotron."""
    ctx = build_compact_context(master, profile=profile, app_defaults=app_defaults, slice_type="tailor")
    salient_jd = extract_salient_jd(job_description, max_chars=2600)

    is_fresher = ctx["experience_level"] == "fresher" or not ctx["experience"]

    system_prompt = (
        "You are the AutoApply Full LaTeX Resume Tailoring Skill powered by Nemotron.\n"
        "Your job is to rebuild EVERY tailorable section of the candidate's resume so it is strongly inclined to the target Job Description while remaining 100% factual.\n\n"
        "STRICT ANTI-FABRICATION RULES:\n"
        "1. NEVER invent employers, job titles, dates, degrees, certifications, projects, fake metrics, or skills not in Verified Profile.\n"
        "2. If Candidate is a Fresher / has no prior corporate experience, NEVER invent internships/companies. Instead, populate `tailored_project_bullets` for EVERY listed project with 3-4 punchy, JD-inclined engineering bullets highlighting architecture, verified technologies, and problem-solving relevant to the target JD.\n"
        "3. Populate `recommended_project_order` placing the project most relevant to the JD first.\n"
        "4. Populate `emphasized_skills` using ONLY verified skills + project technologies, reordered so JD-matching skills come first.\n"
        "5. Populate `tailored_interests` aligning candidate's verified interests/domains with the JD.\n"
        "6. Put required JD skills NOT present in Verified Profile strictly inside `missing_skills_gaps`.\n"
        "7. Write a crisp 3-4 sentence `tailored_summary` referencing the target role/company and verified strengths.\n"
        "8. Draft a concise 3-paragraph `cover_letter` grounded solely in verified facts."
    )

    user_prompt = (
        f"TARGET ROLE: {job_title} at {company}\n"
        f"TARGET JD (COMPACT):\n{salient_jd}\n\n"
        f"CANDIDATE COMPACT CONTEXT ({'FRESHER / STUDENT' if is_fresher else 'EXPERIENCED'}):\n"
        f"{json.dumps(ctx, ensure_ascii=False)}"
    )

    router = llm_router or get_router()
    result, _ = await router.chat_json(
        messages=[
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ],
        response_model=TailoredResumeOutput,
        task="strong",
        temperature=0.2,
        max_retries=2,
    )
    return result  # type: ignore
