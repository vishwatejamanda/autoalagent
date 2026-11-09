"""Cross-portal deduplication service using fuzzy matching and SHA-256 description hashes."""

import hashlib
import re
from typing import Optional, Tuple
from rapidfuzz import fuzz
from sqlmodel import Session, select
from models.job import Job


def compute_description_hash(description: str) -> str:
    """Normalize whitespace and compute SHA-256 hash of job description."""
    cleaned = re.sub(r"\s+", " ", description.lower().strip())
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()


def normalize_string(text: str) -> str:
    """Lowercase and strip non-alphanumeric characters."""
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def is_fuzzy_duplicate(job_a_title: str, job_a_comp: str, job_a_loc: str,
                       job_b_title: str, job_b_comp: str, job_b_loc: str) -> bool:
    """Determine if two jobs are duplicates across different portals using RapidFuzz."""
    norm_comp_a = normalize_string(job_a_comp)
    norm_comp_b = normalize_string(job_b_comp)

    # 1. Company match (token_set_ratio handles Inc, LLC, Systems, Corp suffixes)
    company_score = fuzz.token_set_ratio(norm_comp_a, norm_comp_b)
    if company_score < 80:
        return False

    # 2. Title match
    norm_title_a = normalize_string(job_a_title)
    norm_title_b = normalize_string(job_b_title)
    title_score = fuzz.token_sort_ratio(norm_title_a, norm_title_b)
    if title_score < 85:
        return False

    # 3. Location match (if both provide location)
    if job_a_loc and job_b_loc:
        norm_loc_a = normalize_string(job_a_loc)
        norm_loc_b = normalize_string(job_b_loc)
        loc_score = fuzz.token_set_ratio(norm_loc_a, norm_loc_b)
        if loc_score < 60:
            return False

    return True


def check_duplicate(session: Session, new_job: Job) -> Tuple[bool, Optional[Job]]:
    """Check if new_job already exists via external_id, description hash, or fuzzy match."""
    # 1. Exact external_id + source check
    if new_job.source and new_job.external_id:
        existing = session.exec(
            select(Job)
            .where(Job.source == new_job.source)
            .where(Job.external_id == new_job.external_id)
        ).first()
        if existing:
            return True, existing

    # 2. Exact description hash check
    if new_job.description_hash:
        existing = session.exec(
            select(Job).where(Job.description_hash == new_job.description_hash)
        ).first()
        if existing:
            return True, existing

    # 3. Fuzzy match across existing jobs in the database
    all_recent_jobs = session.exec(select(Job).order_by(Job.id.desc()).limit(200)).all()
    for existing_job in all_recent_jobs:
        if is_fuzzy_duplicate(
            new_job.title, new_job.company, new_job.location,
            existing_job.title, existing_job.company, existing_job.location,
        ):
            return True, existing_job

    return False, None
