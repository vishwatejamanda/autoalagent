"""Answer Bank service: fuzzy question matching, LLM drafting, and safety guards.

HARD RULE: Never auto-answer legal/authorization/salary/disability/demographic
questions without a pre-saved, explicit answer approved by the candidate.
"""

import logging
import re
from typing import Optional, Tuple
from rapidfuzz import fuzz
from sqlmodel import Session, select

from models.settings import AnswerBank
from schemas.profile import MasterProfileData
from llm.provider import LLMMessage
from llm.router import get_router

logger = logging.getLogger(__name__)

# Sensitive categories requiring explicit manual approval
SENSITIVE_PATTERNS = [
    r"authorized to work",
    r"sponsorship",
    r"visa",
    r"salary",
    r"compensation",
    r"ctc",
    r"disability",
    r"veteran",
    r"race",
    r"gender",
    r"criminal",
    r"background check",
    r"felony",
]


def is_sensitive_question(question_text: str) -> bool:
    """Determine whether a question touches legal, salary, or demographic topics."""
    q_lower = question_text.lower()
    return any(re.search(pat, q_lower) for pat in SENSITIVE_PATTERNS)


def find_saved_answer(session: Session, question_text: str) -> Tuple[Optional[str], bool]:
    """Find a saved answer in the AnswerBank using fuzzy matching.
    
    Returns (answer, is_approved).
    """
    answers = session.exec(select(AnswerBank)).all()
    q_norm = question_text.lower().strip()

    best_match: Optional[AnswerBank] = None
    best_ratio = 0.0

    for a in answers:
        pattern_norm = a.pattern.lower().strip()
        # Direct substring match
        if pattern_norm in q_norm or q_norm in pattern_norm:
            best_match = a
            best_ratio = 100.0
            break
        # Fuzzy token sort match
        ratio = fuzz.token_sort_ratio(pattern_norm, q_norm)
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = a

    if best_match and best_ratio >= 78:
        # Check safety guard: if sensitive and not approved, return None
        if is_sensitive_question(question_text) and not best_match.approved:
            return None, False
        return best_match.answer, best_match.approved

    return None, False


async def draft_and_record_answer(
    session: Session,
    question_text: str,
    master: MasterProfileData,
    job_title: str = "",
    company: str = "",
    app_defaults: Optional[dict] = None,
) -> Tuple[str, bool]:
    """Draft an answer via compact form_answer_skill (respecting Fresher/N/A defaults).

    Returns (drafted_answer, requires_approval).
    """
    from llm.skills.form_answer_skill import skill_answer_form_question

    sensitive = is_sensitive_question(question_text)
    category = "legal" if sensitive else "general"

    if app_defaults is None:
        try:
            from api.settings_api import load_application_defaults
            app_defaults = load_application_defaults(session)
        except Exception:
            app_defaults = None

    skill_res = await skill_answer_form_question(
        question=question_text,
        master=master,
        job_title=job_title,
        company=company,
        app_defaults=app_defaults,
    )
    drafted = skill_res.answer

    # Deterministic Application Defaults (e.g. Fresher / N/A / Notice Period) don't need manual approval
    is_deterministic = skill_res.source == "deterministic_default" and not sensitive and not skill_res.requires_human

    # Save to AnswerBank
    new_entry = AnswerBank(
        pattern=question_text[:200],
        category=category,
        answer=drafted,
        approved=is_deterministic,
        times_used=1 if is_deterministic else 0,
    )
    session.add(new_entry)
    session.commit()

    return drafted, (not is_deterministic)

