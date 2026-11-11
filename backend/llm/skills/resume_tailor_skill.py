"""Resume Tailoring AI Skill.

Tailors summary, verified experience/project bullets, verified skills ordering,
areas of interest, and cover letter for a specific Job Description using a
compact context slice (no unused personal/template bloat).
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
        description="Keyed by exact project name for academic/personal projects",
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
    """Run the modular Resume Tailoring skill on a compact context slice."""
    ctx = build_compact_context(master, profile=profile, app_defaults=app_defaults, slice_type="tailor")
    salient_jd = extract_salient_jd(job_description, max_chars=2600)

    is_fresher = ctx["experience_level"] == "fresher" or not ctx["experience"]

    system_prompt = (
        "You are the AutoApply LaTeX Resume Tailoring Skill.\n"
        "Tailor ONLY the candidate's factual summary, bullet wording, skill ordering, and cover letter to the target JD.\n\n"
        "STRICT ANTI-FABRICATION RULES:\n"
        "1. NEVER invent employers, job titles, dates, degrees, certifications, projects, metrics, or skills not in Verified Profile.\n"
        "2. If Candidate has no prior full-time corporate experience (Fresher), NEVER invent internships/jobs; tailor `tailored_project_bullets` keyed by exact project name instead.\n"
        "3. `emphasized_skills` MUST ONLY contain subsets/reordered skills from Verified Skills + project technologies.\n"
        "4. Put required JD skills NOT present in Verified Profile strictly inside `missing_skills_gaps`.\n"
        "5. Keep `tailored_summary` to 3-4 crisp ATS-friendly sentences mentioning alignment with the target company/role.\n"
        "6. Keep project/experience bullets punchy (1-2 lines each) for clean single-page LaTeX PDF layout.\n"
        "7. Draft a concise 3-paragraph cover letter grounded only in verified profile facts."
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

