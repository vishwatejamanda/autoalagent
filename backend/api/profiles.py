"""Profiles & Master Profile API endpoints."""

import json
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session, select

from app.database import get_session
from models.profile import MasterProfile, Profile
from models.audit import AuditLog
from schemas.profile import (
    MasterProfileData,
    MasterProfileResponse,
    MasterProfileUpdate,
    ProfileCreate,
    ProfileUpdate,
    ProfileResponse,
)
from services.resume_parser import extract_text_from_file, parse_resume_to_master_profile
from docs.builder_latex import SAMPLE_STARTER_LATEX, parse_latex_to_master_profile

router = APIRouter(prefix="/profiles", tags=["profiles"])


# ─── Master Profile (Single Source of Truth) ──────────────────


@router.get("/master")
async def get_master_profile(session: Session = Depends(get_session)):
    """Retrieve the single active Master Profile JSON."""
    master = session.exec(select(MasterProfile).order_by(MasterProfile.id.desc())).first()
    if not master:
        # Initialize an empty master profile if none exists
        empty_data = MasterProfileData()
        master = MasterProfile(
            data=empty_data.model_dump_json(),
            version=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(master)
        session.commit()
        session.refresh(master)

    try:
        parsed_data = MasterProfileData.model_validate_json(master.data)
    except Exception:
        parsed_data = MasterProfileData()

    return {
        "id": master.id,
        "data": parsed_data,
        "version": master.version,
        "created_at": master.created_at,
        "updated_at": master.updated_at,
    }


@router.put("/master")
async def update_master_profile(
    body: MasterProfileUpdate,
    session: Session = Depends(get_session),
):
    """Update Master Profile JSON directly."""
    master = session.exec(select(MasterProfile).order_by(MasterProfile.id.desc())).first()
    if not master:
        master = MasterProfile(
            data=body.data.model_dump_json(),
            version=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(master)
    else:
        master.data = body.data.model_dump_json()
        master.version += 1
        master.updated_at = datetime.now(timezone.utc)
        session.add(master)

    session.add(AuditLog(
        action="master_profile_updated",
        entity_type="master_profile",
        details=f"Master profile updated to version {master.version}",
        created_at=datetime.now(timezone.utc),
    ))
    session.commit()
    session.refresh(master)

    return {
        "id": master.id,
        "data": body.data,
        "version": master.version,
        "created_at": master.created_at,
        "updated_at": master.updated_at,
    }


@router.post("/master/upload")
async def upload_resume(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    """Upload a resume (PDF/DOCX) to parse via LLM into Master Profile."""
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    raw_text = extract_text_from_file(file.filename or "resume.pdf", contents)
    parsed_data = await parse_resume_to_master_profile(raw_text)

    # Save to database
    master = session.exec(select(MasterProfile).order_by(MasterProfile.id.desc())).first()
    if not master:
        master = MasterProfile(
            data=parsed_data.model_dump_json(),
            version=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(master)
    else:
        master.data = parsed_data.model_dump_json()
        master.version += 1
        master.updated_at = datetime.now(timezone.utc)
        session.add(master)

    session.add(AuditLog(
        action="master_profile_uploaded",
        entity_type="master_profile",
        details=f"Parsed from uploaded file '{file.filename}', version {master.version}",
        created_at=datetime.now(timezone.utc),
    ))
    session.commit()
    session.refresh(master)

    return {
        "id": master.id,
        "data": parsed_data,
        "version": master.version,
        "filename": file.filename,
        "extracted_chars": len(raw_text),
    }


@router.get("/master/default-latex-template")
async def get_default_latex_template():
    """Return the built-in LaTeX starter resume template."""
    return {"latex": SAMPLE_STARTER_LATEX}


@router.post("/master/import-latex")
async def import_latex_to_master_profile(
    body: dict,
    session: Session = Depends(get_session),
):
    """Parse a raw LaTeX resume template into Master Profile and store its template."""
    latex_code = (body.get("latex") or "").strip()
    if not latex_code:
        raise HTTPException(status_code=400, detail="latex field is required")

    parsed_data = parse_latex_to_master_profile(latex_code)
    if not parsed_data.contact.full_name and not parsed_data.skills and not parsed_data.projects:
        raise HTTPException(status_code=400, detail="Could not parse candidate sections from the provided LaTeX source")

    master = session.exec(select(MasterProfile).order_by(MasterProfile.id.desc())).first()
    if not master:
        master = MasterProfile(
            data=parsed_data.model_dump_json(),
            version=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(master)
    else:
        master.data = parsed_data.model_dump_json()
        master.version += 1
        master.updated_at = datetime.now(timezone.utc)
        session.add(master)

    session.add(AuditLog(
        action="master_profile_latex_imported",
        entity_type="master_profile",
        details=f"Imported Master Profile from LaTeX template, version {master.version}",
        created_at=datetime.now(timezone.utc),
    ))
    session.commit()
    session.refresh(master)

    return {
        "id": master.id,
        "data": parsed_data,
        "version": master.version,
    }


# ─── Job-Hunting Profiles (Personas) CRUD ─────────────────────


def _serialize_profile(p: Profile) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "target_titles": json.loads(p.target_titles or "[]"),
        "include_keywords": json.loads(p.include_keywords or "[]"),
        "exclude_keywords": json.loads(p.exclude_keywords or "[]"),
        "countries": json.loads(p.countries or "[]"),
        "cities": json.loads(p.cities or "[]"),
        "remote_preference": p.remote_preference,
        "min_experience": p.min_experience,
        "max_experience": p.max_experience,
        "salary_expectation": p.salary_expectation,
        "notice_period": p.notice_period,
        "base_resume_emphasis": p.base_resume_emphasis,
        "allowed_portals": json.loads(p.allowed_portals or '["linkedin","naukri","workday"]'),
        "daily_cap": p.daily_cap,
        "auto_apply_mode": p.auto_apply_mode,
        "min_match_score": p.min_match_score,
        "is_active": p.is_active,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }


@router.get("")
async def list_profiles(session: Session = Depends(get_session)):
    """List all job hunting persona profiles."""
    profiles = session.exec(select(Profile).order_by(Profile.id.desc())).all()
    return [_serialize_profile(p) for p in profiles]


@router.post("")
async def create_profile(
    body: ProfileCreate,
    session: Session = Depends(get_session),
):
    """Create a new job hunting profile."""
    profile = Profile(
        name=body.name,
        target_titles=json.dumps(body.target_titles),
        include_keywords=json.dumps(body.include_keywords),
        exclude_keywords=json.dumps(body.exclude_keywords),
        countries=json.dumps(body.countries),
        cities=json.dumps(body.cities),
        remote_preference=body.remote_preference,
        min_experience=body.min_experience,
        max_experience=body.max_experience,
        salary_expectation=body.salary_expectation,
        notice_period=body.notice_period,
        base_resume_emphasis=body.base_resume_emphasis,
        allowed_portals=json.dumps(body.allowed_portals),
        daily_cap=body.daily_cap,
        auto_apply_mode=body.auto_apply_mode,
        min_match_score=body.min_match_score,
        is_active=body.is_active,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(profile)
    session.add(AuditLog(
        action="profile_created",
        entity_type="profile",
        details=f"Created persona profile '{body.name}'",
        created_at=datetime.now(timezone.utc),
    ))
    session.commit()
    session.refresh(profile)
    return _serialize_profile(profile)


@router.get("/{profile_id}")
async def get_profile(profile_id: int, session: Session = Depends(get_session)):
    """Get single profile by ID."""
    p = session.get(Profile, profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _serialize_profile(p)


@router.put("/{profile_id}")
async def update_profile(
    profile_id: int,
    body: ProfileUpdate,
    session: Session = Depends(get_session),
):
    """Update an existing job hunting profile."""
    p = session.get(Profile, profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")

    if body.name is not None:
        p.name = body.name
    if body.target_titles is not None:
        p.target_titles = json.dumps(body.target_titles)
    if body.include_keywords is not None:
        p.include_keywords = json.dumps(body.include_keywords)
    if body.exclude_keywords is not None:
        p.exclude_keywords = json.dumps(body.exclude_keywords)
    if body.countries is not None:
        p.countries = json.dumps(body.countries)
    if body.cities is not None:
        p.cities = json.dumps(body.cities)
    if body.remote_preference is not None:
        p.remote_preference = body.remote_preference
    if body.min_experience is not None:
        p.min_experience = body.min_experience
    if body.max_experience is not None:
        p.max_experience = body.max_experience
    if body.salary_expectation is not None:
        p.salary_expectation = body.salary_expectation
    if body.notice_period is not None:
        p.notice_period = body.notice_period
    if body.base_resume_emphasis is not None:
        p.base_resume_emphasis = body.base_resume_emphasis
    if body.allowed_portals is not None:
        p.allowed_portals = json.dumps(body.allowed_portals)
    if body.daily_cap is not None:
        p.daily_cap = body.daily_cap
    if body.auto_apply_mode is not None:
        p.auto_apply_mode = body.auto_apply_mode
    if body.min_match_score is not None:
        p.min_match_score = body.min_match_score
    if body.is_active is not None:
        p.is_active = body.is_active

    p.updated_at = datetime.now(timezone.utc)
    session.add(p)
    session.commit()
    session.refresh(p)
    return _serialize_profile(p)


@router.delete("/{profile_id}")
async def delete_profile(profile_id: int, session: Session = Depends(get_session)):
    """Delete a profile."""
    p = session.get(Profile, profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    session.delete(p)
    session.add(AuditLog(
        action="profile_deleted",
        entity_type="profile",
        entity_id=profile_id,
        details=f"Deleted profile '{p.name}'",
        created_at=datetime.now(timezone.utc),
    ))
    session.commit()
    return {"deleted": profile_id}

