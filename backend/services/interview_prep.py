"""Interview preparation and company research note generator using LLMRouter.

Generates:
1. Likely technical, behavioral, and role-specific interview questions with tailored talking points
   derived ONLY from the candidate's real profile facts (no fabrication).
2. Company research summary extracted strictly from the Job Description text.
"""

from __future__ import annotations

import json
import logging
from typing import List, Optional
from pydantic import BaseModel, Field

from llm.provider import LLMMessage
from llm.router import LLMRouter

logger = logging.getLogger(__name__)


# ======================================================================
# Schemas
# ======================================================================

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
    questions_for_interviewer: List[str] = Field(
        description="High-impact questions the candidate can ask the interviewers about the role/tech stack",
        default_factory=list,
    )


class CompanyResearchResult(BaseModel):
    company_name: str
    domain_and_mission: str = Field(description="Industry domain, core mission, or market niche")
    product_and_business: str = Field(description="Products, platform, or business operations noted in the JD")
    tech_stack_detected: List[str] = Field(description="Key tools, languages, frameworks, or cloud platforms mentioned")
    team_and_culture_cues: List[str] = Field(description="Work environment, culture values, or collaboration style clues")
    role_impact_summary: str = Field(description="Primary problems and impact this hire is expected to deliver")


# ======================================================================
# Service Functions
# ======================================================================

async def generate_interview_prep(
    job_title: str,
    company: str,
    job_description: str,
    master_profile_json: dict,
    router: Optional[LLMRouter] = None,
) -> InterviewPrepResult:
    """Generate interview prep tailored to JD + real candidate profile facts."""
    if router is None:
        router = LLMRouter()

    system_prompt = (
        "You are an expert technical interview coach and hiring manager.\n"
        "Your task is to prepare a candidate for an upcoming interview based on the Job Description and their Profile.\n\n"
        "CRITICAL ANTI-FABRICATION RULE:\n"
        "- All suggested talking points MUST be grounded strictly in the candidate's actual projects, skills, and experience provided in the profile.\n"
        "- NEVER invent achievements, companies, metrics, or technologies the candidate has not used.\n"
        "- If the JD requires a skill or tool that is NOT in the candidate's profile, explicitly advise on how to address the skill gap honestly (e.g. demonstrating parallel experience or rapid learning).\n"
        "Return valid JSON matching the requested schema."
    )

    user_content = f"""JOB DETAILS:
Title: {job_title}
Company: {company}

JOB DESCRIPTION:
{job_description[:4000]}

CANDIDATE MASTER PROFILE:
{json.dumps(master_profile_json, indent=2)[:3500]}

Generate high-probability interview questions, rationale, tailored talking points strictly from the candidate's facts, and 3-4 insightful questions to ask the interviewer.
"""

    messages = [
        LLMMessage(role="system", content=system_prompt),
        LLMMessage(role="user", content=user_content),
    ]

    result, _ = await router.chat_json(
        messages=messages,
        response_model=InterviewPrepResult,
        task="strong",
        temperature=0.3,
    )
    return result  # type: ignore


async def generate_company_research(
    job_title: str,
    company: str,
    job_description: str,
    router: Optional[LLMRouter] = None,
) -> CompanyResearchResult:
    """Extract company research notes strictly from the Job Description text."""
    if router is None:
        router = LLMRouter()

    system_prompt = (
        "You are a corporate intelligence and career research assistant.\n"
        "Analyze the provided Job Description to synthesize a crisp, factual company research briefing.\n"
        "RULE: Rely ONLY on details discernible from the job description text. Do not invent unsubstantiated corporate trivia.\n"
        "Return valid JSON matching the requested schema."
    )

    user_content = f"""Company: {company}
Role: {job_title}

JOB DESCRIPTION:
{job_description[:4500]}

Synthesize domain, products/platform, identified tech stack, culture cues, and key role impact.
"""

    messages = [
        LLMMessage(role="system", content=system_prompt),
        LLMMessage(role="user", content=user_content),
    ]

    result, _ = await router.chat_json(
        messages=messages,
        response_model=CompanyResearchResult,
        task="cheap",
        temperature=0.2,
    )
    return result  # type: ignore

