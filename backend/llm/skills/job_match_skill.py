"""Job Matching AI Skill (Stage 2 semantic scoring on compact `match` context)."""

from __future__ import annotations

import json
from typing import Any, List, Optional
from pydantic import BaseModel

from llm.provider import LLMMessage
from llm.router import LLMRouter, get_router
from llm.skills.context_builder import build_compact_context, extract_salient_jd
from schemas.profile import MasterProfileData


class LLMMatchResult(BaseModel):
    score: int
    reasoning: str
    matching_skills: List[str] = []
    missing_skills: List[str] = []


async def skill_score_job_match(
    master: MasterProfileData,
    profile: Any,
    job_title: str,
    company: str,
    job_description: str,
    app_defaults: Optional[dict[str, Any]] = None,
    llm_router: Optional[LLMRouter] = None,
) -> LLMMatchResult:
    """Score job fit using the minimal `match` slice + condensed JD."""
    ctx = build_compact_context(master, profile=profile, app_defaults=app_defaults, slice_type="match")
    salient_jd = extract_salient_jd(job_description, max_chars=2000)

    system_prompt = (
        "You are the AutoApply Job Fit Evaluator Skill.\n"
        "Score how well the candidate matches the role from 0 to 100.\n"
        "CRITICAL EXPERIENCE RULE: If the candidate is a fresher / max_experience <= 1 and the JD clearly requires 2+ years of professional experience, penalize the score heavily (<= 35) and note the experience gap.\n"
        "Return strict JSON matching schema: {score, reasoning, matching_skills, missing_skills}."
    )
    user_prompt = (
        f"JOB: {job_title} at {company}\n"
        f"JD:\n{salient_jd}\n\n"
        f"CANDIDATE MATCH CONTEXT:\n{json.dumps(ctx, ensure_ascii=False)}"
    )

    router = llm_router or get_router()
    result, _ = await router.chat_json(
        messages=[
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ],
        response_model=LLMMatchResult,
        task="cheap",
        temperature=0.1,
    )
    return result  # type: ignore

