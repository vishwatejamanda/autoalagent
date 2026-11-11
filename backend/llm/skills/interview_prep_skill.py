"""Interview Preparation & Company Research AI Skills.

Uses the compact `interview` context slice and tailors coaching specifically
for freshers (emphasizing projects, coursework, hackathons) or experienced
candidates as appropriate.
"""

from __future__ import annotations

import json
from typing import Any, List, Optional
from pydantic import BaseModel, Field

from llm.provider import LLMMessage
from llm.router import LLMRouter, get_router
from llm.skills.context_builder import build_compact_context, extract_salient_jd
from schemas.profile import MasterProfileData


class InterviewQuestion(BaseModel):
    question: str = Field(description="The interview question")
    category: str = Field(description="Technical, Behavioral, or Domain/System Design")
    why_asked: str = Field(description="What the hiring team is evaluating with this question")
    suggested_talking_points: List[str] = Field(
        description="Key points from the candidate's real profile to highlight. NO FABRICATIONS."
    )


class InterviewPrepResult(BaseModel):
    role_overview: str = Field(description="Brief assessment of the role focus and priority themes")
    technical_questions: List[InterviewQuestion] = Field(default_factory=list)
    behavioral_questions: List[InterviewQuestion] = Field(default_factory=list)
    questions_for_interviewer: List[str] = Field(default_factory=list)


class CompanyResearchResult(BaseModel):
    company_name: str
    domain_and_mission: str
    product_and_business: str
    tech_stack_detected: List[str]
    team_and_culture_cues: List[str]
    role_impact_summary: str


async def skill_prepare_interview(
    master: MasterProfileData,
    job_title: str,
    company: str,
    job_description: str,
    app_defaults: Optional[dict[str, Any]] = None,
    llm_router: Optional[LLMRouter] = None,
) -> InterviewPrepResult:
    """Generate role-grounded interview prep from compact `interview` context."""
    ctx = build_compact_context(master, app_defaults=app_defaults, slice_type="interview")
    salient_jd = extract_salient_jd(job_description, max_chars=2600)
    is_fresher = ctx["experience_level"] == "fresher" or not ctx["experience"]

    fresher_guidance = (
        "Since this candidate is a FRESHER / final-year student, anchor technical deep-dives around their Projects, "
        "Core CS fundamentals, and Certifications rather than nonexistent past corporate jobs.\n"
        if is_fresher
        else ""
    )

    system_prompt = (
        "You are the AutoApply Interview Preparation Skill.\n"
        f"{fresher_guidance}"
        "CRITICAL ANTI-FABRICATION RULE:\n"
        "- Talking points MUST reference ONLY verified projects, experience, education, skills, and achievements in the context.\n"
        "- NEVER invent metrics, companies, or tools not listed.\n"
        "- For any JD skill missing from profile, suggest honest bridging strategies using adjacent verified skills.\n"
        "Return valid JSON matching the requested schema."
    )

    user_prompt = (
        f"ROLE: {job_title} at {company}\n"
        f"JD:\n{salient_jd}\n\n"
        f"CANDIDATE COMPACT CONTEXT:\n{json.dumps(ctx, ensure_ascii=False)}"
    )

    router = llm_router or get_router()
    result, _ = await router.chat_json(
        messages=[
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ],
        response_model=InterviewPrepResult,
        task="strong",
        temperature=0.3,
    )
    return result  # type: ignore


async def skill_company_research(
    job_title: str,
    company: str,
    job_description: str,
    llm_router: Optional[LLMRouter] = None,
) -> CompanyResearchResult:
    """Synthesize company intelligence strictly from salient JD content."""
    salient_jd = extract_salient_jd(job_description, max_chars=2800)

    system_prompt = (
        "You are the AutoApply Company Research Skill.\n"
        "Extract factual domain, product, tech stack, culture cues, and role impact strictly from the Job Description.\n"
        "Do NOT invent external trivia not supported by the text."
    )
    user_prompt = f"Company: {company}\nRole: {job_title}\n\nJD:\n{salient_jd}"

    router = llm_router or get_router()
    result, _ = await router.chat_json(
        messages=[
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ],
        response_model=CompanyResearchResult,
        task="cheap",
        temperature=0.2,
    )
    return result  # type: ignore

