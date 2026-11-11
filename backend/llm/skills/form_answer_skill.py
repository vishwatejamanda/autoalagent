"""Application Form Q&A AI Skill.

Answers portal screening questions cleanly using deterministic Fresher / N/A
application defaults first, and the compact `form` context slice for free-form
custom questions — never hallucinating prior employers or CTC values.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional
from pydantic import BaseModel

from llm.provider import LLMMessage
from llm.router import LLMRouter, get_router
from llm.skills.context_builder import build_compact_context
from schemas.profile import MasterProfileData


class FormAnswerResult(BaseModel):
    answer: str
    confidence: float = 0.85
    source: str = "skill_llm"  # deterministic_default | skill_llm | pause_sensitive
    requires_human: bool = False


_RULE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(previous|current|last)\s*(company|employer|organization)\b", re.I), "previous_company"),
    (re.compile(r"\b(previous|current|last)\s*(role|title|designation)\b", re.I), "previous_role"),
    (re.compile(r"\b(current|present)\s*(ctc|salary|compensation|package)\b", re.I), "current_ctc"),
    (re.compile(r"\b(expected|desired)\s*(ctc|salary|compensation|package)\b", re.I), "expected_ctc"),
    (re.compile(r"\b(total|overall|years\s*of)\s*experience\b|\bhow\s*many\s*years\b", re.I), "years_of_experience"),
    (re.compile(r"\bnotice\s*period\b|\bwhen\s*can\s*you\s*join\b|\bavailability\b", re.I), "notice_period"),
    (re.compile(r"\brelocate\b|\brelocation\b", re.I), "willing_to_relocate"),
    (re.compile(r"\b(work\s*auth|authorized\s*to\s*work|legally\s*eligible)\b", re.I), "work_authorization"),
    (re.compile(r"\b(full\s*name|your\s*name|legal\s*name)\b", re.I), "full_name"),
    (re.compile(r"\b(email|e-mail)\b", re.I), "email"),
    (re.compile(r"\b(phone|mobile|contact\s*number)\b", re.I), "phone"),
    (re.compile(r"\b(city|current\s*location|address)\b", re.I), "location"),
    (re.compile(r"\blinkedin\b", re.I), "linkedin"),
    (re.compile(r"\bgithub\b", re.I), "github"),
    (re.compile(r"\b(portfolio|website)\b", re.I), "portfolio"),
]


async def skill_answer_form_question(
    question: str,
    master: MasterProfileData,
    job_title: str = "",
    company: str = "",
    app_defaults: Optional[dict[str, Any]] = None,
    llm_router: Optional[LLMRouter] = None,
) -> FormAnswerResult:
    """Resolve an application screening question deterministically or via compact `form` AI skill."""
    ctx = build_compact_context(master, app_defaults=app_defaults, slice_type="form")

    # 1. Fast deterministic rule lookup (zero LLM tokens!)
    for pattern, key in _RULE_PATTERNS:
        if pattern.search(question):
            val = str(ctx.get(key) or "N/A").strip() or "N/A"
            return FormAnswerResult(
                answer=val,
                confidence=0.98,
                source="deterministic_default",
                requires_human=False,
            )

    # Skills question shortcut
    if re.search(r"\b(top\s*skills|key\s*skills|technical\s*skills|technologies)\b", question, re.I):
        skills_str = ", ".join(ctx.get("skills", [])[:12])
        if skills_str:
            return FormAnswerResult(answer=skills_str, confidence=0.95, source="deterministic_default")

    # 2. Compact LLM answer using `form` context slice only
    system_prompt = (
        "You are the AutoApply Portal Form Question Skill.\n"
        "Answer the job application form question concisely (1-3 sentences max, or a direct numeric/Yes/No value if asked).\n"
        "HARD RULES:\n"
        "- If candidate is a fresher (`experience_level == 'fresher'`) and asked for prior corporate experience/salary, respond honestly with '0' / 'Fresher' / 'N/A' as appropriate.\n"
        "- NEVER invent employers, years of experience, or skills not listed in Candidate Context.\n"
        "- If question asks for confidential IDs (SSN/Aadhaar/PAN/Passport) or password/OTP, set requires_human=true."
    )
    user_prompt = (
        f"JOB: {job_title} at {company}\n"
        f"QUESTION: {question}\n\n"
        f"COMPACT APPLICANT CONTEXT:\n{json.dumps(ctx, ensure_ascii=False)}"
    )

    try:
        router = llm_router or get_router()
        result, _ = await router.chat_json(
            messages=[
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(role="user", content=user_prompt),
            ],
            response_model=FormAnswerResult,
            task="cheap",
            temperature=0.1,
        )
        return result  # type: ignore
    except Exception:
        return FormAnswerResult(answer="N/A", confidence=0.4, source="deterministic_default", requires_human=False)

