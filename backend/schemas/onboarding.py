"""Pydantic schemas for the CareerOps-aligned Onboarding and Doctor system."""

from __future__ import annotations

from typing import Any, List, Optional
from pydantic import BaseModel, Field


class CandidateAnswers(BaseModel):
    full_name: str = ""
    email: str = ""
    location: str = ""
    timezone: str = ""
    phone: str = ""
    linkedin: str = ""
    portfolio_url: str = ""
    github: str = ""
    twitter: str = ""
    years_of_experience: int = 0


class CompensationAnswers(BaseModel):
    target_range: str = ""
    currency: str = "USD"
    minimum: str = ""
    location_flexibility: str = "any"


class LocationAnswers(BaseModel):
    country: str = ""
    city: str = ""
    timezone: str = ""
    visa_status: str = "authorized"
    authorized_in: List[str] = Field(default_factory=list)
    needs_sponsorship: bool = False


class ArchetypeEntry(BaseModel):
    name: str = ""
    level: str = "Entry"  # Entry, Mid, Senior, Lead, Staff
    fit: str = "primary"  # primary, secondary, adjacent


class ProofPoint(BaseModel):
    name: str = ""
    url: str = ""
    hero_metric: str = ""


class NarrativeAnswers(BaseModel):
    headline: str = ""
    exit_story: str = ""
    superpowers: List[str] = Field(default_factory=list)
    proof_points: List[ProofPoint] = Field(default_factory=list)
    excites: str = ""
    drains: str = ""
    deal_breakers: List[str] = Field(default_factory=list)


class ExperienceFilter(BaseModel):
    stretch_years: int = 1
    action: str = "label"  # "label" or "drop"


class PortalsAnswers(BaseModel):
    positive: List[str] = Field(default_factory=list)
    negative: List[str] = Field(default_factory=list)
    countries: List[str] = Field(default_factory=list)
    cities: List[str] = Field(default_factory=list)
    max_posting_age_days: int = 45
    experience_filter: ExperienceFilter = Field(default_factory=ExperienceFilter)


class CvAnswers(BaseModel):
    raw_markdown: str = ""
    linkedin_url: str = ""
    max_pages: int = 1
    strict_pages: bool = False


class OnboardingAnswers(BaseModel):
    spend_tier: str = "standard"  # economy, standard, premium
    candidate: CandidateAnswers = Field(default_factory=CandidateAnswers)
    target_roles: List[str] = Field(default_factory=list)
    compensation: CompensationAnswers = Field(default_factory=CompensationAnswers)
    location: LocationAnswers = Field(default_factory=LocationAnswers)
    archetypes: List[ArchetypeEntry] = Field(default_factory=list)
    narrative: NarrativeAnswers = Field(default_factory=NarrativeAnswers)
    portals: PortalsAnswers = Field(default_factory=PortalsAnswers)
    cv: CvAnswers = Field(default_factory=CvAnswers)


class DoctorCheckItem(BaseModel):
    name: str
    status: str  # "ok", "warning", "error"
    message: str
    details: Optional[str] = None


class DoctorReport(BaseModel):
    passed: bool
    data_root: str
    onboarding_needed: bool
    missing_files: List[str] = Field(default_factory=list)
    unpersonalized_fields: List[str] = Field(default_factory=list)
    checks: List[DoctorCheckItem] = Field(default_factory=list)


class OnboardingStatusResponse(BaseModel):
    onboarding_needed: bool
    completed_steps: List[str] = Field(default_factory=list)
    doctor: DoctorReport
    answers: Optional[OnboardingAnswers] = None
