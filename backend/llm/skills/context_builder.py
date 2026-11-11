"""Compact context slicer for AI skills.

Reduces token usage and latency by sending only the profile fields relevant to
a specific task (`tailor`, `interview`, `match`, `form`) and normalizing
Fresher / N/A defaults consistently across all skills.
"""

from __future__ import annotations

import re
from typing import Any, Optional

from schemas.profile import MasterProfileData


DEFAULT_APPLICATION_DEFAULTS: dict[str, Any] = {
    "experience_level": "fresher",
    "years_of_experience": "0",
    "previous_company": "N/A",
    "previous_role": "N/A",
    "current_ctc": "N/A",
    "expected_ctc": "As per company standards",
    "notice_period": "Immediate",
    "willing_to_relocate": "Yes",
    "work_authorization": "Authorized to work in India",
    "key_skills": "",
    "custom_qa_notes": "",
}


def extract_salient_jd(jd_text: str, max_chars: int = 2400) -> str:
    """Condense repetitive boilerplate from a Job Description while keeping
    responsibilities, requirements, skills, and experience criteria.
    """
    if not jd_text:
        return ""
    # Collapse excess whitespace/blank lines
    lines = [re.sub(r"\s+", " ", line).strip() for line in jd_text.splitlines()]
    cleaned = [ln for ln in lines if ln]
    joined = "\n".join(cleaned)
    if len(joined) <= max_chars:
        return joined

    # Keep first 1100 chars (role/intro/requirements) + any lines mentioning skills/exp/qualifications
    head = joined[:1100]
    tail_candidates = []
    kw = re.compile(
        r"(responsibilit|require|qualif|skill|experienc|tech|stack|proficien|educat|bachelor|degree|fresher|year)",
        re.I,
    )
    for ln in cleaned:
        if ln not in head and kw.search(ln):
            tail_candidates.append(ln)
    tail = "\n".join(tail_candidates)
    combined = f"{head}\n...\n{tail}"
    return combined[:max_chars]


def _normalize_defaults(app_defaults: Optional[dict[str, Any]], master: MasterProfileData) -> dict[str, Any]:
    merged = dict(DEFAULT_APPLICATION_DEFAULTS)
    if app_defaults:
        for k, v in app_defaults.items():
            if v is not None and str(v).strip() != "":
                merged[k] = v

    # Derive fresher flag cleanly when experience list is empty
    if not master.experience and merged.get("experience_level", "").lower() in ("fresher", "0", "na", "n/a", ""):
        merged["experience_level"] = "fresher"
        if not merged.get("years_of_experience"):
            merged["years_of_experience"] = "0"
        if not merged.get("previous_company"):
            merged["previous_company"] = "N/A"
    elif master.experience and app_defaults is None:
        merged["experience_level"] = "experienced"
        merged["previous_company"] = master.experience[0].company or "N/A"
        merged["previous_role"] = master.experience[0].title or "N/A"

    if not merged.get("key_skills") and master.skills:
        merged["key_skills"] = ", ".join(master.skills[:20])
    return merged


def build_compact_context(
    master: MasterProfileData,
    profile: Optional[Any] = None,
    app_defaults: Optional[dict[str, Any]] = None,
    slice_type: str = "tailor",
) -> dict[str, Any]:
    """Return a task-scoped compact dict from MasterProfileData + Profile + Defaults.

    Supported `slice_type` values:
    - ``tailor``: Summary, skills, experience (or fresher projects), education titles, certs, interests.
    - ``interview``: Experience level, projects, experience bullets, top skills, achievements.
    - ``match``: Role targets, keywords, experience range, location, skills, project tech stack.
    - ``form``: Contact info, N/A/Fresher application defaults, degree summary, skills.
    """
    defaults = _normalize_defaults(app_defaults, master)
    all_project_tech = []
    for p in master.projects:
        all_project_tech.extend(p.technologies or [])
    unique_tech = list(dict.fromkeys([*master.skills, *all_project_tech]))

    if slice_type == "match":
        target_titles = getattr(profile, "target_titles", []) if profile else []
        include_kw = getattr(profile, "include_keywords", []) if profile else []
        exclude_kw = getattr(profile, "exclude_keywords", []) if profile else []
        min_exp = getattr(profile, "min_experience", 0) if profile else 0
        max_exp = getattr(profile, "max_experience", 0) if profile else 0
        return {
            "experience_level": defaults["experience_level"],
            "years_of_experience": defaults["years_of_experience"],
            "target_titles": target_titles,
            "include_keywords": include_kw,
            "exclude_keywords": exclude_kw,
            "min_experience": min_exp,
            "max_experience": max_exp,
            "skills": unique_tech[:35],
            "education": [e.degree for e in master.education[:2]],
        }

    if slice_type == "form":
        top_edu = master.education[0] if master.education else None
        return {
            "full_name": master.contact.full_name,
            "email": master.contact.email,
            "phone": master.contact.phone,
            "location": master.contact.location,
            "linkedin": master.contact.linkedin,
            "github": master.contact.github,
            "portfolio": master.contact.portfolio,
            "experience_level": defaults["experience_level"],
            "years_of_experience": defaults["years_of_experience"],
            "previous_company": defaults["previous_company"],
            "previous_role": defaults["previous_role"],
            "current_ctc": defaults["current_ctc"],
            "expected_ctc": defaults["expected_ctc"],
            "notice_period": defaults["notice_period"],
            "willing_to_relocate": defaults["willing_to_relocate"],
            "work_authorization": defaults["work_authorization"],
            "education": f"{top_edu.degree} ({top_edu.institution}, {top_edu.graduation_date})" if top_edu else "N/A",
            "skills": unique_tech[:25],
            "projects": [{"name": p.name, "tech": p.technologies[:6]} for p in master.projects[:3]],
            "custom_qa_notes": defaults.get("custom_qa_notes", ""),
        }

    if slice_type == "interview":
        return {
            "name": master.contact.full_name,
            "experience_level": defaults["experience_level"],
            "summary": master.summary[:500],
            "skills": master.skills[:30],
            "experience": [
                {"company": e.company, "title": e.title, "bullets": e.bullets[:4]}
                for e in master.experience[:4]
            ],
            "projects": [
                {
                    "name": p.name,
                    "technologies": p.technologies[:8],
                    "bullets": (p.bullets or ([p.description] if p.description else []))[:4],
                }
                for p in master.projects[:4]
            ],
            "education": [f"{e.degree} - {e.institution} ({e.graduation_date})" for e in master.education[:2]],
            "certifications": [c.name for c in master.certifications[:5]],
            "achievements": master.achievements[:5],
        }

    # Default: "tailor"
    return {
        "name": master.contact.full_name,
        "experience_level": defaults["experience_level"],
        "summary": master.summary[:700],
        "skills": master.skills[:40],
        "experience": [
            {"key": f"{e.company}_{e.title}", "company": e.company, "title": e.title, "bullets": e.bullets[:5]}
            for e in master.experience
        ],
        "projects": [
            {
                "key": p.name,
                "name": p.name,
                "technologies": p.technologies,
                "bullets": p.bullets if p.bullets else ([p.description] if p.description else []),
            }
            for p in master.projects
        ],
        "education": [
            {"degree": e.degree, "institution": e.institution, "courses": e.relevant_courses[:8]}
            for e in master.education[:2]
        ],
        "certifications": [f"{c.name} ({c.date})" for c in master.certifications],
        "achievements": master.achievements,
        "areas_of_interest": getattr(master, "areas_of_interest", []),
        "persona_emphasis": getattr(profile, "base_resume_emphasis", "") if profile else "",
    }

