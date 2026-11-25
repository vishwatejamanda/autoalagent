"""FastAPI router for Onboarding and Doctor system."""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from schemas.onboarding import (
    DoctorReport,
    OnboardingAnswers,
    OnboardingStatusResponse,
)
from services.onboarding import (
    get_current_onboarding_status,
    init_personalization_templates,
    run_doctor,
    save_onboarding_answers,
    sync_markdown_tracker,
    validate_cv_markdown,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


class ValidateCvRequest(BaseModel):
    markdown: str


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_status() -> OnboardingStatusResponse:
    """Get overall onboarding completion status and pre-filled answers."""
    try:
        return get_current_onboarding_status()
    except Exception as exc:
        logger.exception("Failed to compute onboarding status: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/doctor", response_model=DoctorReport)
async def doctor_check() -> DoctorReport:
    """Run CareerOps doctor diagnostic checks."""
    try:
        return run_doctor()
    except Exception as exc:
        logger.exception("Failed to run doctor checks: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/setup", response_model=DoctorReport)
async def complete_onboarding(answers: OnboardingAnswers) -> DoctorReport:
    """Save full onboarding configuration across user layer files, database, and tracker."""
    try:
        return save_onboarding_answers(answers)
    except Exception as exc:
        logger.exception("Failed to save onboarding configuration: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/validate-cv")
async def validate_cv(body: ValidateCvRequest) -> Dict[str, Any]:
    """Validate Markdown CV structure against standard headings and return parsed preview."""
    passed, errors, parsed = validate_cv_markdown(body.markdown)
    return {
        "valid": passed,
        "errors": errors,
        "parsed_preview": parsed.model_dump(),
    }


@router.post("/sync-tracker")
async def sync_tracker() -> Dict[str, Any]:
    """Synchronize database applications into data/applications.md."""
    try:
        count = sync_markdown_tracker()
        return {"success": True, "count": count, "file": "data/applications.md"}
    except Exception as exc:
        logger.exception("Failed to sync markdown tracker: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/init-templates")
async def init_templates() -> Dict[str, Any]:
    """Initialize missing personalization files from default templates."""
    try:
        copied = init_personalization_templates()
        return {"success": True, "copied": copied}
    except Exception as exc:
        logger.exception("Failed to initialize templates: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
