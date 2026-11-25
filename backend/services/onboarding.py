"""Onboarding & System Doctor Service based on CareerOps architecture.

Implements the first-run onboarding sequence, markdown CV parsing and validation,
YAML profile and portal generation, application tracker synchronization, and
system health diagnostics.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from sqlmodel import Session, select

from app.config import get_settings
from app.database import engine
from models.application import Application, Resume
from models.job import Job, JobScore
from models.profile import MasterProfile, Profile
from models.settings import Setting
from schemas.onboarding import (
    CandidateAnswers,
    CompensationAnswers,
    CvAnswers,
    DoctorCheckItem,
    DoctorReport,
    ExperienceFilter,
    LocationAnswers,
    NarrativeAnswers,
    OnboardingAnswers,
    OnboardingStatusResponse,
    PortalsAnswers,
)
from schemas.profile import (
    CertificationEntry,
    ContactInfo,
    EducationEntry,
    ExperienceEntry,
    MasterProfileData,
    ProjectEntry,
)

logger = logging.getLogger(__name__)

NOT_A_PLACE_RE = re.compile(r"^(remote|hybrid|anywhere|on-?site)$", re.IGNORECASE)
EXPERIENCE_HEADING_RE = re.compile(
    r"^##\s+(?:Work\s+Experience|Professional\s+Experience|Employment\s+History|Work\s+History|Experience)",
    re.IGNORECASE | re.MULTILINE,
)
SKILLS_HEADING_RE = re.compile(r"^##\s+.*(?:Skill|Technical|Technologies).*", re.IGNORECASE | re.MULTILINE)
PROJECTS_HEADING_RE = re.compile(r"^##\s+.*(?:Project|Portfolio).*", re.IGNORECASE | re.MULTILINE)
EDUCATION_HEADING_RE = re.compile(r"^##\s+.*(?:Education|Academic).*", re.IGNORECASE | re.MULTILINE)


def get_data_dir() -> Path:
    """Return the resolved data root directory."""
    settings = get_settings()
    data_dir = Path(settings.BROWSER_PROFILE_DIR).parent
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_personalization_paths() -> Dict[str, Path]:
    """Map canonical personalization file names to paths inside data root."""
    root = get_data_dir()
    modes_dir = root / "modes"
    modes_dir.mkdir(parents=True, exist_ok=True)
    return {
        "cv": root / "cv.md",
        "profile": root / "profile.yml",
        "portals": root / "portals.yml",
        "applications": root / "applications.md",
        "voice_dna": root / "voice-dna.md",
        "mode_profile": modes_dir / "_profile.md",
        "mode_custom": modes_dir / "_custom.md",
        "mode_brief": modes_dir / "_brief.md",
    }


def init_personalization_templates() -> List[str]:
    """Initialize missing personalization files from templates; existing files are preserved."""
    paths = get_personalization_paths()
    copied: List[str] = []

    defaults = {
        "voice_dna": "# Candidate Voice DNA\n\nTone: Professional, technical, concise.\nAvoid hyperbole or corporate clichés.\n",
        "mode_profile": "# Target Roles & Framing Overrides\n\n- Primary focus: Technical Software Engineering & AI Solutions\n",
        "mode_custom": "# Procedural House Rules\n\n- Generate 1-page CVs for fresher applications.\n- Never fabricate metrics or employment history.\n",
        "mode_brief": "# Daily Brief Preferences\n\n- Alert for matching scores >= 70.\n",
        "applications": "# Applications Tracker\n\n| # | Date | Company | Role | Score | Status | PDF | Report | Notes |\n|---|------|---------|------|-------|--------|-----|--------|-------|\n",
    }

    for key, content in defaults.items():
        file_path = paths[key]
        if not file_path.exists():
            file_path.write_text(content, encoding="utf-8")
            copied.append(str(file_path.name))

    return copied


def validate_cv_markdown(text: str) -> Tuple[bool, List[str], MasterProfileData]:
    """Validate Markdown CV structure against CareerOps standard and extract profile data.
    
    Verifies:
    - Experience heading: ## Experience / ## Work Experience
    - Job items: ### Company — Location or ### Company, with bold title
    - Skills section: ## Skills
    - Projects / Education sections
    """
    errors: List[str] = []
    lines = text.strip().splitlines()
    data = MasterProfileData()

    if not text.strip():
        return False, ["CV text is empty."], data

    has_exp = bool(EXPERIENCE_HEADING_RE.search(text))
    has_skills = bool(SKILLS_HEADING_RE.search(text))

    if not has_exp:
        errors.append("Missing Experience heading (e.g. '## Work Experience' or '## Experience').")
    if not has_skills:
        errors.append("Missing Skills heading (e.g. '## Technical Skills' or '## Skills').")

    # Parse sections roughly into MasterProfileData
    current_section = ""
    current_company = ""
    current_job_bullets: List[str] = []
    current_job_title = ""
    current_job_dates = ""

    current_project_name = ""
    current_proj_bullets: List[str] = []

    summary_lines: List[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# ") and not current_section:
            data.contact.full_name = stripped.lstrip("# ").strip()
            continue

        if stripped.startswith("## "):
            sec_name = stripped.lstrip("# ").strip().lower()
            if "experience" in sec_name or "employment" in sec_name or "history" in sec_name:
                current_section = "experience"
            elif "skill" in sec_name or "technolog" in sec_name:
                current_section = "skills"
            elif "project" in sec_name:
                current_section = "projects"
            elif "education" in sec_name:
                current_section = "education"
            elif "summary" in sec_name or "profile" in sec_name:
                current_section = "summary"
            elif "certif" in sec_name:
                current_section = "certifications"
            continue

        if current_section == "summary":
            if stripped:
                summary_lines.append(stripped)
        elif current_section == "skills":
            clean_line = stripped.lstrip("-* ").strip()
            if ":" in clean_line:
                _, clean_line = clean_line.split(":", 1)
            for part in re.split(r"[,;]\s*", clean_line):
                clean = re.sub(r"^\*\*[^*]+\*\*:\s*", "", part).strip()
                clean = clean.strip("*").strip()
                if clean and clean not in data.skills:
                    data.skills.append(clean)
        elif current_section == "experience":
            if stripped.startswith("### "):
                if current_company and current_job_title:
                    data.experience.append(
                        ExperienceEntry(
                            title=current_job_title,
                            company=current_company,
                            start_date=current_job_dates,
                            bullets=list(current_job_bullets),
                        )
                    )
                current_job_bullets = []
                current_company = stripped.lstrip("# ").strip()
                current_job_title = ""
                current_job_dates = ""
            elif stripped.startswith("**") and stripped.endswith("**"):
                current_job_title = stripped.strip("*").strip()
            elif re.search(r"\b(20\d\d|19\d\d)\b", stripped) and not current_job_bullets and not stripped.startswith("-"):
                current_job_dates = stripped
            elif stripped.startswith(("-", "*")):
                current_job_bullets.append(stripped.lstrip("-* ").strip())
        elif current_section == "projects":
            if stripped.startswith("### "):
                if current_project_name:
                    data.projects.append(
                        ProjectEntry(
                            name=current_project_name,
                            bullets=list(current_proj_bullets),
                        )
                    )
                current_proj_bullets = []
                current_project_name = stripped.lstrip("# ").strip()
            elif stripped.startswith(("-", "*")):
                current_proj_bullets.append(stripped.lstrip("-* ").strip())
        elif current_section == "education":
            if stripped.startswith(("-", "*", "###")):
                deg_text = stripped.lstrip("-*# ").strip()
                if deg_text:
                    data.education.append(EducationEntry(degree=deg_text))

    # Flush last experience / project
    if current_company and current_job_title:
        data.experience.append(
            ExperienceEntry(
                title=current_job_title,
                company=current_company,
                start_date=current_job_dates,
                bullets=list(current_job_bullets),
            )
        )
    if current_project_name:
        data.projects.append(
            ProjectEntry(
                name=current_project_name,
                bullets=list(current_proj_bullets),
            )
        )

    if summary_lines:
        data.summary = " ".join(summary_lines)

    passed = len(errors) == 0
    return passed, errors, data


def run_doctor() -> DoctorReport:
    """Run comprehensive system diagnostics matching CareerOps doctor checks."""
    paths = get_personalization_paths()
    checks: List[DoctorCheckItem] = []
    missing_files: List[str] = []
    unpersonalized_fields: List[str] = []

    # 1. Check Data Root & Marker
    root = get_data_dir()
    checks.append(
        DoctorCheckItem(
            name="Data Root",
            status="ok",
            message=f"Resolved at {root}",
            details=str(root.resolve()),
        )
    )

    # 2. Check CV
    cv_path = paths["cv"]
    if not cv_path.exists() or cv_path.stat().st_size == 0:
        missing_files.append("cv.md")
        checks.append(
            DoctorCheckItem(
                name="CV Document",
                status="warning",
                message="cv.md is missing or empty. Run Step 1 onboarding to ingest your CV.",
            )
        )
    else:
        cv_text = cv_path.read_text(encoding="utf-8")
        valid, cv_errors, _ = validate_cv_markdown(cv_text)
        if valid:
            checks.append(
                DoctorCheckItem(
                    name="CV Structure",
                    status="ok",
                    message="cv.md has valid sections (Experience, Skills, Headings).",
                )
            )
        else:
            checks.append(
                DoctorCheckItem(
                    name="CV Structure",
                    status="warning",
                    message=f"CV format warnings: {'; '.join(cv_errors)}",
                )
            )

    # 3. Check Profile YAML
    prof_path = paths["profile"]
    if not prof_path.exists() or prof_path.stat().st_size == 0:
        missing_files.append("config/profile.yml")
        checks.append(
            DoctorCheckItem(
                name="Candidate Profile",
                status="warning",
                message="profile.yml is missing. Run Step 2 to configure personal details.",
            )
        )
    else:
        try:
            prof_data = yaml.safe_load(prof_path.read_text(encoding="utf-8")) or {}
            cand = prof_data.get("candidate", {})
            if not cand.get("full_name") or not cand.get("email"):
                unpersonalized_fields.extend(["candidate.full_name", "candidate.email"])
            roles = prof_data.get("target_roles", [])
            if not roles:
                unpersonalized_fields.append("target_roles")

            if unpersonalized_fields:
                checks.append(
                    DoctorCheckItem(
                        name="Candidate Profile",
                        status="warning",
                        message=f"Profile has unpersonalized fields: {', '.join(unpersonalized_fields)}",
                    )
                )
            else:
                checks.append(
                    DoctorCheckItem(
                        name="Candidate Profile",
                        status="ok",
                        message=f"Profile configured for {cand.get('full_name')} targeting {len(roles)} roles.",
                    )
                )
        except Exception as e:
            checks.append(
                DoctorCheckItem(
                    name="Candidate Profile",
                    status="error",
                    message=f"Failed to parse profile.yml: {e}",
                )
            )

    # 4. Check Portals YAML
    portals_path = paths["portals"]
    if not portals_path.exists() or portals_path.stat().st_size == 0:
        missing_files.append("portals.yml")
        checks.append(
            DoctorCheckItem(
                name="Portals Configuration",
                status="warning",
                message="portals.yml is missing. Run Step 3 to configure search filters.",
            )
        )
    else:
        try:
            pdata = yaml.safe_load(portals_path.read_text(encoding="utf-8")) or {}
            pos = pdata.get("portals", {}).get("positive", [])
            loc = pdata.get("location_filter", {})
            allow = loc.get("allow", []) + loc.get("always_allow", [])
            has_not_place = any(NOT_A_PLACE_RE.search(str(x)) for x in allow)

            if has_not_place:
                checks.append(
                    DoctorCheckItem(
                        name="Portals Configuration",
                        status="error",
                        message="Location filter contains 'Remote' or 'Hybrid' as place. Use specific countries/cities.",
                    )
                )
            elif not pos:
                checks.append(
                    DoctorCheckItem(
                        name="Portals Configuration",
                        status="warning",
                        message="Positive title keywords list is empty.",
                    )
                )
            else:
                checks.append(
                    DoctorCheckItem(
                        name="Portals Configuration",
                        status="ok",
                        message=f"Configured with {len(pos)} positive keywords and clean location allowlist.",
                    )
                )
        except Exception as e:
            checks.append(
                DoctorCheckItem(
                    name="Portals Configuration",
                    status="error",
                    message=f"Failed to parse portals.yml: {e}",
                )
            )

    # 5. Check Applications Tracker
    app_path = paths["applications"]
    if not app_path.exists():
        missing_files.append("data/applications.md")
        checks.append(
            DoctorCheckItem(
                name="Applications Tracker",
                status="warning",
                message="applications.md is missing. It will be initialized on first scan/apply.",
            )
        )
    else:
        content = app_path.read_text(encoding="utf-8")
        if "| Company |" in content and "| Role |" in content:
            checks.append(
                DoctorCheckItem(
                    name="Applications Tracker",
                    status="ok",
                    message="applications.md tracker table is initialized and verified.",
                )
            )
        else:
            checks.append(
                DoctorCheckItem(
                    name="Applications Tracker",
                    status="warning",
                    message="applications.md exists but header table is non-standard.",
                )
            )

    # 6. Check LLM Provider
    settings = get_settings()
    provider = settings.DEFAULT_PROVIDER
    has_nvidia = bool(settings.NVIDIA_API_KEY and not settings.NVIDIA_API_KEY.startswith("your-"))
    has_mistral = bool(settings.MISTRAL_API_KEY and not settings.MISTRAL_API_KEY.startswith("your-"))

    if provider == "nvidia" and has_nvidia:
        checks.append(
            DoctorCheckItem(
                name="LLM Provider",
                status="ok",
                message=f"NVIDIA Nemotron active ({settings.NVIDIA_STRONG_MODEL}).",
            )
        )
    elif provider == "mistral" and has_mistral:
        checks.append(
            DoctorCheckItem(
                name="LLM Provider",
                status="ok",
                message=f"Mistral active ({settings.MISTRAL_STRONG_MODEL}).",
            )
        )
    else:
        checks.append(
            DoctorCheckItem(
                name="LLM Provider",
                status="warning",
                message=f"Provider '{provider}' configured, but valid API key is missing.",
            )
        )

    # 7. Check Playwright Chromium Browser
    browser_dir = Path(settings.BROWSER_PROFILE_DIR)
    browser_dir.mkdir(parents=True, exist_ok=True)
    checks.append(
        DoctorCheckItem(
            name="Browser Environment",
            status="ok",
            message=f"Browser profile directory ready at {browser_dir}",
        )
    )

    onboarding_needed = len(missing_files) > 0 or len(unpersonalized_fields) > 0
    passed = not any(c.status == "error" for c in checks) and not onboarding_needed

    return DoctorReport(
        passed=passed,
        data_root=str(root),
        onboarding_needed=onboarding_needed,
        missing_files=missing_files,
        unpersonalized_fields=unpersonalized_fields,
        checks=checks,
    )


def sync_markdown_tracker() -> int:
    """Synchronize database applications into data/applications.md markdown tracker table."""
    paths = get_personalization_paths()
    tracker_path = paths["applications"]

    with Session(engine) as session:
        statement = select(Application, Job).join(Job, Application.job_id == Job.id).order_by(Application.id.desc())
        results = session.exec(statement).all()

        lines = [
            "# Applications Tracker",
            "",
            "| # | Date | Company | Role | Score | Status | PDF | Report | Notes |",
            "|---|------|---------|------|-------|--------|-----|--------|-------|",
        ]

        for app, job in results:
            dt = app.applied_at.strftime("%Y-%m-%d") if app.applied_at else app.created_at.strftime("%Y-%m-%d")
            score_row = session.exec(select(JobScore).where(JobScore.job_id == job.id).order_by(JobScore.id.desc())).first()
            score = str(score_row.score) if score_row else "-"
            status = app.status.upper()
            pdf_link = f"[PDF](/api/resumes/{app.resume_id}/pdf)" if app.resume_id else "-"
            report_link = f"[Job](/api/jobs/{job.id})"
            notes = (app.error_message or app.mode).replace("|", "\\|")
            lines.append(
                f"| {app.id} | {dt} | {job.company} | {job.title} | {score} | {status} | {pdf_link} | {report_link} | {notes} |"
            )

        tracker_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return len(results)


def save_onboarding_answers(answers: OnboardingAnswers) -> DoctorReport:
    """Save full onboarding configuration across User Layer files and database."""
    paths = get_personalization_paths()
    init_personalization_templates()

    # 1. Write profile.yml
    profile_payload = {
        "candidate": {
            "full_name": answers.candidate.full_name,
            "email": answers.candidate.email,
            "location": answers.candidate.location,
            "timezone": answers.candidate.timezone or answers.location.timezone,
            "phone": answers.candidate.phone,
            "linkedin": answers.candidate.linkedin,
            "portfolio_url": answers.candidate.portfolio_url,
            "github": answers.candidate.github,
            "twitter": answers.candidate.twitter,
            "years_of_experience": answers.candidate.years_of_experience,
        },
        "target_roles": answers.target_roles,
        "compensation": {
            "target_range": answers.compensation.target_range,
            "currency": answers.compensation.currency,
            "minimum": answers.compensation.minimum,
            "location_flexibility": answers.compensation.location_flexibility,
        },
        "location": {
            "country": answers.location.country,
            "city": answers.location.city,
            "timezone": answers.location.timezone,
            "visa_status": answers.location.visa_status,
            "authorized_in": answers.location.authorized_in,
            "needs_sponsorship": answers.location.needs_sponsorship,
        },
        "spend_tier": answers.spend_tier,
        "cv": {
            "max_pages": answers.cv.max_pages,
            "strict_pages": answers.cv.strict_pages,
        },
        "archetypes": [a.model_dump() for a in answers.archetypes],
        "narrative": answers.narrative.model_dump(),
    }

    paths["profile"].write_text(
        "# CareerOps Candidate Profile\n# Generated by Onboarding System\n" + yaml.dump(profile_payload, sort_keys=False),
        encoding="utf-8",
    )

    # 2. Write portals.yml
    # Reject remote/hybrid as places in location filter
    clean_countries = [c for c in answers.portals.countries if not NOT_A_PLACE_RE.search(c)]
    clean_cities = [c for c in answers.portals.cities if not NOT_A_PLACE_RE.search(c)]

    portals_payload = {
        "portals": {
            "positive": answers.portals.positive or answers.target_roles,
            "negative": answers.portals.negative,
            "max_posting_age_days": answers.portals.max_posting_age_days,
            "experience_filter": answers.portals.experience_filter.model_dump(),
        },
        "location_filter": {
            "always_allow": clean_countries,
            "allow": clean_countries + clean_cities,
        },
    }

    paths["portals"].write_text(
        "# CareerOps Portals Configuration\n# Generated by Onboarding System\n" + yaml.dump(portals_payload, sort_keys=False),
        encoding="utf-8",
    )

    # 3. Write cv.md if raw text provided
    parsed_cv_data: Optional[MasterProfileData] = None
    if answers.cv.raw_markdown.strip():
        paths["cv"].write_text(answers.cv.raw_markdown.strip(), encoding="utf-8")
        _, _, parsed_cv_data = validate_cv_markdown(answers.cv.raw_markdown)

    # 4. Sync Database MasterProfile & Search Profile
    with Session(engine) as session:
        # Update MasterProfile
        master_row = session.exec(select(MasterProfile).order_by(MasterProfile.version.desc())).first()
        if not master_row:
            master_data = parsed_cv_data or MasterProfileData()
            master_data.contact.full_name = answers.candidate.full_name or master_data.contact.full_name
            master_data.contact.email = answers.candidate.email or master_data.contact.email
            master_data.contact.phone = answers.candidate.phone or master_data.contact.phone
            master_data.contact.location = answers.candidate.location or master_data.contact.location
            master_data.contact.linkedin = answers.candidate.linkedin or master_data.contact.linkedin
            master_data.contact.github = answers.candidate.github or master_data.contact.github
            master_data.contact.portfolio = answers.candidate.portfolio_url or master_data.contact.portfolio
            master_row = MasterProfile(data=master_data.model_dump_json(), version=1)
            session.add(master_row)
        else:
            try:
                existing_data = MasterProfileData.model_validate_json(master_row.data)
            except Exception:
                existing_data = MasterProfileData()
            if parsed_cv_data:
                if parsed_cv_data.experience:
                    existing_data.experience = parsed_cv_data.experience
                if parsed_cv_data.projects:
                    existing_data.projects = parsed_cv_data.projects
                if parsed_cv_data.skills:
                    existing_data.skills = parsed_cv_data.skills
                if parsed_cv_data.education:
                    existing_data.education = parsed_cv_data.education
                if parsed_cv_data.summary:
                    existing_data.summary = parsed_cv_data.summary

            if answers.candidate.full_name:
                existing_data.contact.full_name = answers.candidate.full_name
            if answers.candidate.email:
                existing_data.contact.email = answers.candidate.email
            if answers.candidate.phone:
                existing_data.contact.phone = answers.candidate.phone
            if answers.candidate.location:
                existing_data.contact.location = answers.candidate.location
            if answers.candidate.linkedin:
                existing_data.contact.linkedin = answers.candidate.linkedin
            if answers.candidate.github:
                existing_data.contact.github = answers.candidate.github
            if answers.candidate.portfolio_url:
                existing_data.contact.portfolio = answers.candidate.portfolio_url

            master_row.data = existing_data.model_dump_json()
            master_row.version += 1
            session.add(master_row)

        # Update or create active search Profile
        search_profile = session.exec(select(Profile).where(Profile.is_active == True)).first()
        pos_titles = answers.portals.positive or answers.target_roles
        countries_json = json.dumps(clean_countries)
        cities_json = json.dumps(clean_cities)
        target_titles_json = json.dumps(pos_titles)
        exclude_json = json.dumps(answers.portals.negative)

        min_exp = 0
        max_exp = max(answers.candidate.years_of_experience + answers.portals.experience_filter.stretch_years, 2)

        if not search_profile:
            search_profile = Profile(
                name=answers.target_roles[0] if answers.target_roles else "Default Search Profile",
                target_titles=target_titles_json,
                include_keywords=target_titles_json,
                exclude_keywords=exclude_json,
                countries=countries_json,
                cities=cities_json,
                min_experience=min_exp,
                max_experience=max_exp,
                salary_expectation=answers.compensation.target_range,
                is_active=True,
            )
            session.add(search_profile)
        else:
            search_profile.target_titles = target_titles_json
            search_profile.include_keywords = target_titles_json
            search_profile.exclude_keywords = exclude_json
            search_profile.countries = countries_json
            search_profile.cities = cities_json
            search_profile.min_experience = min_exp
            search_profile.max_experience = max_exp
            search_profile.salary_expectation = answers.compensation.target_range
            session.add(search_profile)

        # Update application defaults
        is_fresher = answers.candidate.years_of_experience <= 1
        defaults_map = {
            "experience_level": "fresher" if is_fresher else "experienced",
            "previous_company": "N/A" if is_fresher else "",
            "years_of_experience": str(answers.candidate.years_of_experience),
            "spend_tier": answers.spend_tier,
        }
        for k, v in defaults_map.items():
            st = session.exec(
                select(Setting).where(Setting.category == "application_defaults", Setting.key == k)
            ).first()
            if not st:
                session.add(Setting(category="application_defaults", key=k, value=v))
            else:
                st.value = v
                session.add(st)

        session.commit()

    # 5. Sync applications tracker
    sync_markdown_tracker()

    return run_doctor()


def get_current_onboarding_status() -> OnboardingStatusResponse:
    """Retrieve current onboarding status and prefilled answers if available."""
    paths = get_personalization_paths()
    doc = run_doctor()

    completed: List[str] = []
    answers = OnboardingAnswers()

    if paths["profile"].exists():
        try:
            pdata = yaml.safe_load(paths["profile"].read_text(encoding="utf-8")) or {}
            cand = pdata.get("candidate", {})
            answers.candidate = CandidateAnswers(**cand)
            answers.target_roles = pdata.get("target_roles", [])
            comp = pdata.get("compensation", {})
            answers.compensation = CompensationAnswers(**comp)
            loc = pdata.get("location", {})
            answers.location = LocationAnswers(**loc)
            answers.spend_tier = pdata.get("spend_tier", "standard")
            if pdata.get("archetypes"):
                answers.archetypes = [ArchetypeEntry(**a) for a in pdata["archetypes"]]
            if pdata.get("narrative"):
                answers.narrative = NarrativeAnswers(**pdata["narrative"])
            if pdata.get("cv"):
                answers.cv.max_pages = pdata["cv"].get("max_pages", 1)
                answers.cv.strict_pages = pdata["cv"].get("strict_pages", False)

            if answers.candidate.full_name and answers.candidate.email:
                completed.append("profile")
            if answers.spend_tier:
                completed.append("spend_tier")
        except Exception as e:
            logger.warning("Could not prefill onboarding answers from profile.yml: %s", e)

    if paths["cv"].exists() and paths["cv"].stat().st_size > 0:
        completed.append("cv")
        answers.cv.raw_markdown = paths["cv"].read_text(encoding="utf-8")

    if paths["portals"].exists():
        try:
            ptdata = yaml.safe_load(paths["portals"].read_text(encoding="utf-8")) or {}
            psec = ptdata.get("portals", {})
            answers.portals.positive = psec.get("positive", [])
            answers.portals.negative = psec.get("negative", [])
            answers.portals.max_posting_age_days = psec.get("max_posting_age_days", 45)
            if psec.get("experience_filter"):
                answers.portals.experience_filter = ExperienceFilter(**psec["experience_filter"])
            lsec = ptdata.get("location_filter", {})
            answers.portals.countries = lsec.get("always_allow", [])
            answers.portals.cities = [c for c in lsec.get("allow", []) if c not in answers.portals.countries]
            if answers.portals.positive:
                completed.append("portals")
        except Exception as e:
            logger.warning("Could not prefill portals answers: %s", e)

    if paths["applications"].exists():
        completed.append("tracker")

    return OnboardingStatusResponse(
        onboarding_needed=doc.onboarding_needed,
        completed_steps=completed,
        doctor=doc,
        answers=answers,
    )
