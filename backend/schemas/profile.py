from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


# --- Master Profile Schemas ---


class ContactInfo(BaseModel):
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    github: str = ""
    portfolio: str = ""


class ExperienceEntry(BaseModel):
    title: str = ""
    company: str = ""
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    is_current: bool = False
    bullets: List[str] = []


class ProjectEntry(BaseModel):
    name: str = ""
    description: str = ""
    technologies: List[str] = []
    url: str = ""
    bullets: List[str] = []


class EducationEntry(BaseModel):
    degree: str = ""
    institution: str = ""
    location: str = ""
    graduation_date: str = ""
    gpa: str = ""
    relevant_courses: List[str] = []


class CertificationEntry(BaseModel):
    name: str = ""
    issuer: str = ""
    date: str = ""
    credential_id: str = ""
    url: str = ""


class MasterProfileData(BaseModel):
    """The full master profile structure stored as JSON."""

    contact: ContactInfo = ContactInfo()
    summary: str = ""
    experience: List[ExperienceEntry] = []
    projects: List[ProjectEntry] = []
    skills: List[str] = []
    education: List[EducationEntry] = []
    certifications: List[CertificationEntry] = []
    achievements: List[str] = []


class MasterProfileResponse(BaseModel):
    id: int
    data: MasterProfileData
    version: int
    created_at: datetime
    updated_at: datetime


class MasterProfileUpdate(BaseModel):
    data: MasterProfileData


# --- Search Profile Schemas ---


class ProfileCreate(BaseModel):
    name: str
    target_titles: List[str] = []
    include_keywords: List[str] = []
    exclude_keywords: List[str] = []
    countries: List[str] = []
    cities: List[str] = []
    remote_preference: str = "any"
    min_experience: int = 0
    max_experience: int = 3
    salary_expectation: str = ""
    notice_period: str = ""
    base_resume_emphasis: str = ""
    allowed_portals: List[str] = ["linkedin", "naukri", "workday"]
    daily_cap: int = 50
    auto_apply_mode: str = "off"
    min_match_score: int = 60
    is_active: bool = True


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    target_titles: Optional[List[str]] = None
    include_keywords: Optional[List[str]] = None
    exclude_keywords: Optional[List[str]] = None
    countries: Optional[List[str]] = None
    cities: Optional[List[str]] = None
    remote_preference: Optional[str] = None
    min_experience: Optional[int] = None
    max_experience: Optional[int] = None
    salary_expectation: Optional[str] = None
    notice_period: Optional[str] = None
    base_resume_emphasis: Optional[str] = None
    allowed_portals: Optional[List[str]] = None
    daily_cap: Optional[int] = None
    auto_apply_mode: Optional[str] = None
    min_match_score: Optional[int] = None
    is_active: Optional[bool] = None


class ProfileResponse(BaseModel):
    id: int
    name: str
    target_titles: List[str] = []
    include_keywords: List[str] = []
    exclude_keywords: List[str] = []
    countries: List[str] = []
    cities: List[str] = []
    remote_preference: str = "any"
    min_experience: int = 0
    max_experience: int = 3
    salary_expectation: str = ""
    notice_period: str = ""
    base_resume_emphasis: str = ""
    allowed_portals: List[str] = []
    daily_cap: int = 50
    auto_apply_mode: str = "off"
    min_match_score: int = 60
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
