"""Two-stage job matching and ranking service.

Stage 1: Cheap rule filter (title keywords, exclude list, experience range, location).
Stage 2: LLM scoring (0-100) vs Candidate Profile (skills match, domain fit, red flags).
"""

import json
import logging
import re
from typing import Any, List, Optional, Tuple
from pydantic import BaseModel

from sqlmodel import Session, select
from models.job import Job, JobScore
from models.profile import Profile, MasterProfile
from schemas.profile import MasterProfileData
from llm.skills.job_match_skill import skill_score_job_match

logger = logging.getLogger(__name__)


class LLMScoringResult(BaseModel):
    score: int  # 0 to 100
    reasons: List[str] = []
    missing_skills: List[str] = []
    red_flags: List[str] = []


def stage1_rule_filter(
    job: Job,
    profile: Profile,
    app_defaults: Optional[dict[str, Any]] = None,
) -> Tuple[bool, List[str]]:
    """Stage 1: Fast deterministic heuristic filter. Returns (passed, rejection_reasons)."""
    reasons = []

    title_lower = (job.title or "").lower()
    desc_text = job.description or ""
    desc_lower = desc_text.lower()

    effective_max_exp = profile.max_experience if profile.max_experience is not None else 0
    if app_defaults and str(app_defaults.get("experience_level", "")).lower() == "fresher":
        try:
            yrs = int(float(str(app_defaults.get("years_of_experience", "0") or 0)))
        except ValueError:
            yrs = 0
        effective_max_exp = min(effective_max_exp, yrs)

    # 1. Check exclude keywords (e.g. Senior, Lead, Director if max_experience < 4)
    exclude_keywords = json.loads(profile.exclude_keywords or "[]")
    for kw in exclude_keywords:
        if kw.lower() in title_lower:
            reasons.append(f"Contains excluded keyword in title: '{kw}'")

    if effective_max_exp <= 3:
        senior_terms = ["senior", "sr", "lead", "staff", "principal", "director", "vp", "head of", "architect", "manager", "iii", "iv"]
        if effective_max_exp > 1:
            senior_terms = ["senior", "lead", "staff", "principal", "director", "vp", "head of", "architect"]
        for st in senior_terms:
            if re.search(rf"\b{re.escape(st)}\b", title_lower):
                reasons.append(f"Seniority mismatch for max {effective_max_exp} yrs: found '{st}'")

    # 2. Check title inclusion keywords
    include_keywords = json.loads(profile.include_keywords or "[]")
    if include_keywords:
        has_include = any(ik.lower() in title_lower for ik in include_keywords)
        if not has_include:
            reasons.append("Title does not match any required include keywords")

    # 3. Check years required in description (especially strict for Fresher / <=1 yr profiles)
    years_match = re.search(
        r"(\d+)\+?\s*(?:to|-|–)?\s*(\d+)?\s*(?:years?|yrs?)\s*(?:of\s*)?(?:relevant\s*)?(?:experience|exp)",
        desc_text,
        re.IGNORECASE,
    )
    if years_match:
        min_req = int(years_match.group(1))
        allows_fresher = any(tok in desc_lower for tok in ("fresher", "entry level", "entry-level", "0 year", "0-1", "0 - 1", "0 to 1", "internship"))
        if effective_max_exp <= 1 and min_req >= 2 and not allows_fresher:
            reasons.append(f"Requires {min_req}+ years, exceeds fresher/entry profile max {effective_max_exp}")
        elif min_req > effective_max_exp + 2:
            reasons.append(f"Requires {min_req}+ years, exceeds profile max {effective_max_exp}")

    # 4. Remote preference check (only reject if explicit onsite-only requirement conflicts with remote preference)
    if (profile.remote_preference or "").lower() == "remote":
        onsite_only_patterns = ["onsite only", "on-site only", "100% onsite", "100% on-site", "no remote"]
        if any(pat in desc_lower or pat in title_lower for pat in onsite_only_patterns):
            reasons.append("Requires strict onsite presence; profile preference is remote")

    passed = len(reasons) == 0
    return passed, reasons


async def stage2_llm_score(
    job: Job,
    profile: Profile,
    master: MasterProfileData,
    app_defaults: Optional[dict[str, Any]] = None,
) -> LLMScoringResult:
    """Stage 2: Compact context-sliced LLM scoring (0-100)."""
    try:
        res = await skill_score_job_match(
            master=master,
            profile=profile,
            job_title=job.title,
            company=job.company,
            job_description=job.description,
            app_defaults=app_defaults,
        )
        return LLMScoringResult(
            score=res.score,
            reasons=[res.reasoning] if res.reasoning else [],
            missing_skills=res.missing_skills,
            red_flags=[],
        )
    except Exception as exc:
        logger.warning("LLM scoring skill failed (%s); using heuristic fallback", exc)
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
    force_rescore: bool = False,
    app_defaults: Optional[dict[str, Any]] = None,
) -> JobScore:
    """Run stage 1 and stage 2 scoring, saving or updating a JobScore record."""
    if app_defaults is None:
        try:
            from api.settings_api import load_application_defaults
            app_defaults = load_application_defaults(session)
        except Exception:
            app_defaults = None

    # Check if already scored
    existing = session.exec(
        select(JobScore).where(JobScore.job_id == job.id).where(JobScore.profile_id == profile.id)
    ).first()
    if existing and not force_rescore:
        return existing

    # Auto-hydrate short job description (e.g. Workday CXS detail fetch)
    if not job.description or len(job.description) < 150:
        if job.source == "workday":
            try:
                from sources.workday import WorkdaySource
                job = await WorkdaySource().fetch_details(job)
                session.add(job)
                session.commit()
                session.refresh(job)
            except Exception as exc:
                logger.debug("Auto-hydrate Workday error: %s", exc)

    # Stage 1: Rule Filter
    passed, rejection_reasons = stage1_rule_filter(job, profile, app_defaults=app_defaults)
    if not passed:
        if existing:
            existing.score = 25
            existing.reasons = json.dumps(rejection_reasons)
            existing.gaps = json.dumps([])
            existing.red_flags = json.dumps(["Failed Stage 1 Rule Filter"])
            score_rec = existing
        else:
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
    llm_result = await stage2_llm_score(job, profile, master, app_defaults=app_defaults)

    if existing:
        existing.score = llm_result.score
        existing.reasons = json.dumps(llm_result.reasons)
        existing.gaps = json.dumps(llm_result.missing_skills)
        existing.red_flags = json.dumps(llm_result.red_flags)
        score_rec = existing
    else:
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
    elif llm_result.score < profile.min_match_score and job.status == "matched":
        job.status = "new"
        session.add(job)

    session.commit()
    session.refresh(score_rec)
    return score_rec

