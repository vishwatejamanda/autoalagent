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
) -> Tuple[str, bool]:
    """Draft an answer from the Master Profile via LLM and save as 'needs approval'.
    
    Returns (drafted_answer, requires_approval).
    """
    sensitive = is_sensitive_question(question_text)
    category = "legal" if sensitive else "general"

    # Call LLM to draft answer strictly based on master profile facts
    system_prompt = (
        "You are an assistant answering job application questions on behalf of a candidate.\n"
        "Draft a factual, concise, professional answer (1-2 sentences) derived ONLY from the candidate profile.\n"
        "If you do not know or if it is a yes/no question, provide the most standard factual answer."
    )
    user_prompt = (
        f"Question: {question_text}\n"
        f"Candidate Summary: {master.summary}\n"
        f"Candidate Skills: {', '.join(master.skills)}"
    )

    drafted = ""
    try:
        router = get_router()
        resp = await router.chat(
            messages=[
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(role="user", content=user_prompt),
            ],
            task="cheap",
            temperature=0.0,
        )
        drafted = resp.content.strip()
    except Exception:
        drafted = "Please review candidate resume for details."

    # Save to AnswerBank marked 'approved = False'
    new_entry = AnswerBank(
        pattern=question_text[:200],
        category=category,
        answer=drafted,
        approved=False,
        times_used=0,
    )
    session.add(new_entry)
    session.commit()

    return drafted, True

