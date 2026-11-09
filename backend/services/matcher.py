"""Two-stage job matching and ranking service.

Stage 1: Cheap rule filter (title keywords, exclude list, experience range, location).
Stage 2: LLM scoring (0-100) vs Candidate Profile (skills match, domain fit, red flags).
"""

import json
import logging
import re
from typing import List, Tuple
from pydantic import BaseModel

from sqlmodel import Session, select
from models.job import Job, JobScore
from models.profile import Profile, MasterProfile
from schemas.profile import MasterProfileData
from llm.provider import LLMMessage
from llm.router import get_router

logger = logging.getLogger(__name__)


class LLMScoringResult(BaseModel):
    score: int  # 0 to 100
    reasons: List[str] = []
    missing_skills: List[str] = []
    red_flags: List[str] = []


def stage1_rule_filter(job: Job, profile: Profile) -> Tuple[bool, List[str]]:
    """Stage 1: Fast deterministic heuristic filter. Returns (passed, rejection_reasons)."""
    reasons = []

    title_lower = job.title.lower()

    # 1. Check exclude keywords (e.g. Senior, Lead, Director if max_experience < 4)
    exclude_keywords = json.loads(profile.exclude_keywords or "[]")
    for kw in exclude_keywords:
        if kw.lower() in title_lower:
            reasons.append(f"Contains excluded keyword in title: '{kw}'")

    if profile.max_experience <= 3:
        senior_terms = ["senior", "lead", "staff", "principal", "director", "vp", "head of", "architect"]
        for st in senior_terms:
            if re.search(rf"\b{st}\b", title_lower):
                reasons.append(f"Seniority mismatch for max {profile.max_experience} yrs: found '{st}'")

    # 2. Check title inclusion keywords
    include_keywords = json.loads(profile.include_keywords or "[]")
    if include_keywords:
        has_include = any(ik.lower() in title_lower for ik in include_keywords)
        if not has_include:
            reasons.append("Title does not match any required include keywords")

    # 3. Check years required in description (if present)
    years_match = re.search(r"(\d+)\+?\s*(?:to\s*(\d+))?\s*(?:years?|yrs?)\s*(?:of\s*)?experience", job.description, re.IGNORECASE)
    if years_match:
        min_req = int(years_match.group(1))
        if min_req > profile.max_experience + 2:
            reasons.append(f"Requires {min_req}+ years, exceeds profile max {profile.max_experience}")

    passed = len(reasons) == 0
    return passed, reasons


async def stage2_llm_score(
    job: Job,
    profile: Profile,
    master: MasterProfileData,
) -> LLMScoringResult:
    """Stage 2: LLM scoring (0-100) analyzing skills fit, domain alignment, and red flags."""
    system_prompt = (
        "You are an expert technical recruiter assessing job-fit for a candidate.\n"
        "Evaluate how well the candidate matches the Job Description on a scale of 0 to 100.\n\n"
        "SCORING GUIDELINES:\n"
        "- 80-100: Strong match; core skills present, good domain fit.\n"
        "- 60-79: Moderate match; most skills present, few minor gaps.\n"
        "- 0-59: Poor fit or severe red flags (e.g. requires security clearance, strict onsite when candidate wants remote, mandatory 8+ yrs).\n\n"
        "Return structured JSON with:\n"
        "- score: int (0-100)\n"
        "- reasons: list of concise positive reasons (2-3 items)\n"
        "- missing_skills: list of skills mentioned in JD that candidate lacks\n"
        "- red_flags: list of potential blockers (visa, bond, travel, onsite restriction)"
    )

    user_prompt = (
        f"--- JOB POSTING ---\n"
        f"Title: {job.title}\n"
        f"Company: {job.company}\n"
        f"Location: {job.location}\n"
        f"Description:\n{job.description[:3500]}\n\n"
        f"--- CANDIDATE PROFILE ---\n"
        f"Skills: {json.dumps(master.skills)}\n"
        f"Remote Preference: {profile.remote_preference}\n"
        f"Experience Level: {profile.min_experience}-{profile.max_experience} years\n"
        f"Target Persona: {profile.name} ({profile.base_resume_emphasis})"
    )

    try:
        router = get_router()
        result, _ = await router.chat_json(
            messages=[
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(role="user", content=user_prompt),
            ],
            response_model=LLMScoringResult,
            task="cheap",
            temperature=0.1,
            max_retries=1,
        )
        return result
    except Exception as exc:
        logger.warning("LLM scoring call failed (%s); using heuristic fallback", exc)
        # Deterministic scoring fallback
        candidate_skills_lower = {s.lower() for s in master.skills}
        jd_lower = job.description.lower()
        matched = [s for s in master.skills if s.lower() in jd_lower]
        score = min(max(int((len(matched) / max(len(master.skills), 1)) * 100), 40), 90)
        return LLMScoringResult(
            score=score,
            reasons=[f"Matches {len(matched)} candidate skills"],
            missing_skills=[],
            red_flags=[],
        )


async def score_job_for_profile(
    session: Session,
    job: Job,
    profile: Profile,
    master: MasterProfileData,
) -> JobScore:
    """Run stage 1 and stage 2 scoring, saving a JobScore record."""
    # Check if already scored
    existing = session.exec(
        select(JobScore).where(JobScore.job_id == job.id).where(JobScore.profile_id == profile.id)
    ).first()
    if existing:
        return existing

    # Stage 1: Rule Filter
    passed, rejection_reasons = stage1_rule_filter(job, profile)
    if not passed:
        score_rec = JobScore(
            job_id=job.id or 1,
            profile_id=profile.id or 1,
            score=25,
            reasons=json.dumps(rejection_reasons),
            gaps=json.dumps([]),
            red_flags=json.dumps(["Failed Stage 1 Rule Filter"]),
        )
        session.add(score_rec)
        session.commit()
        session.refresh(score_rec)
        return score_rec

    # Stage 2: LLM Scoring
    llm_result = await stage2_llm_score(job, profile, master)

    score_rec = JobScore(
        job_id=job.id or 1,
        profile_id=profile.id or 1,
        score=llm_result.score,
        reasons=json.dumps(llm_result.reasons),
        gaps=json.dumps(llm_result.missing_skills),
        red_flags=json.dumps(llm_result.red_flags),
    )
    session.add(score_rec)

    # Update job status if score is high
    if llm_result.score >= profile.min_match_score and job.status == "new":
        job.status = "matched"
        session.add(job)

    session.commit()
    session.refresh(score_rec)
    return score_rec

