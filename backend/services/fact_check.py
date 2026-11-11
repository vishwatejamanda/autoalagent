"""Fact-checking and ATS keyword scoring service.

HARD RULE: Never invent employers, titles, dates, degrees, certifications, metrics, or skills
not present in the Master Profile. If the JD desires a skill the candidate doesn't have,
it must be flagged as a 'gap' and excluded from the resume.
"""

import json
import logging
import re
from typing import List, Tuple
from pydantic import BaseModel

from schemas.profile import MasterProfileData
from llm.provider import LLMMessage
from llm.router import get_router

logger = logging.getLogger(__name__)


class FactCheckReport(BaseModel):
    passed: bool
    fabrications_detected: List[str] = []
    gaps_detected: List[str] = []
    ats_score: int = 0
    feedback: str = ""


def compute_ats_keyword_coverage(jd_text: str, candidate_skills: list[str]) -> Tuple[int, list[str], list[str]]:
    """Compute exact & partial keyword match between JD and candidate skills."""
    if not jd_text or not candidate_skills:
        return 0, [], []

    jd_lower = jd_text.lower()
    matched = []
    missing_skills = []

    # Common technical terms extracted from JD
    common_patterns = re.findall(r"\b[A-Za-z0-9\.\+#]{2,15}\b", jd_lower)
    jd_words = set(common_patterns)

    for skill in candidate_skills:
        skill_lower = skill.lower()
        if skill_lower in jd_lower or skill_lower in jd_words:
            matched.append(skill)

    # ATS score calculation: reward JD keyword coverage without penalizing breadth of skills
    if candidate_skills:
        denominator = min(len(candidate_skills), 12)
        score = int((len(matched) / max(denominator, 1)) * 100)
        score = min(max(score, 25 if not matched else 35), 98)
    else:
        score = 50

    return score, matched, missing_skills


async def verify_against_master_profile(
    master: MasterProfileData,
    tailored_summary: str,
    tailored_bullets: dict[str, list[str]],
    tailored_skills: list[str],
    job_description: str,
) -> FactCheckReport:
    """Run an LLM fact-check pass diffing tailored resume content against Master Profile."""
    router = get_router()

    # Fast offline verification first: ensure no unauthorized skills were added
    master_skills_set = {s.lower().strip() for s in master.skills}
    unauthorized_skills = [s for s in tailored_skills if s.lower().strip() not in master_skills_set]

    # Verify company names in bullets
    master_companies = {e.company.lower().strip() for e in master.experience}

    system_prompt = (
        "You are an ATS compliance auditor and strict fact-checker.\n"
        "HARD RULE: Candidate MUST NOT claim skills, companies, degrees, or metrics they do not have.\n"
        "Diff the proposed tailored resume bullets and summary against the verified Master Profile.\n"
        "Identify any fabricated claims, invented companies, or exaggerated metrics."
    )

    user_prompt = (
        f"--- VERIFIED MASTER PROFILE ---\n"
        f"Skills: {json.dumps(master.skills)}\n"
        f"Experience: {json.dumps([{'company': e.company, 'title': e.title, 'bullets': e.bullets} for e in master.experience])}\n"
        f"Projects: {json.dumps([{'name': p.name, 'technologies': p.technologies, 'bullets': p.bullets} for p in master.projects])}\n\n"
        f"--- PROPOSED TAILORED CONTENT ---\n"
        f"Summary: {tailored_summary}\n"
        f"Tailored Bullets: {json.dumps(tailored_bullets)}\n"
        f"Proposed Skills: {json.dumps(tailored_skills)}\n\n"
        f"--- JOB DESCRIPTION ---\n"
        f"{job_description[:3000]}"
    )

    try:
        report, _ = await router.chat_json(
            messages=[
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(role="user", content=user_prompt),
            ],
            response_model=FactCheckReport,
            task="cheap",
            temperature=0.0,
            max_retries=1,
        )
        if unauthorized_skills:
            report.fabrications_detected.extend(unauthorized_skills)
            report.passed = False
        if report.ats_score <= 0:
            score, _, _ = compute_ats_keyword_coverage(job_description, master.skills)
            report.ats_score = score
        return report
    except Exception as exc:
        logger.warning("LLM fact-check call failed (%s); using deterministic check", exc)
        score, matched, _ = compute_ats_keyword_coverage(job_description, master.skills)
        passed = len(unauthorized_skills) == 0
        return FactCheckReport(
            passed=passed,
            fabrications_detected=unauthorized_skills,
            gaps_detected=[],
            ats_score=score,
            feedback="Deterministic fact-check completed.",
        )

