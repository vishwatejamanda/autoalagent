from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel

from models.base import TimestampMixin, utcnow


class MasterProfile(TimestampMixin, SQLModel, table=True):
    __tablename__ = "masterprofile"

    id: Optional[int] = Field(default=None, primary_key=True)
    data: str = ""  # JSON string of the full master profile structure
    version: int = 1


class Profile(TimestampMixin, SQLModel, table=True):
    __tablename__ = "profile"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = ""  # e.g. "Software Engineer"
    target_titles: str = "[]"  # JSON array of job titles
    include_keywords: str = "[]"  # JSON array
    exclude_keywords: str = "[]"  # JSON array
    countries: str = "[]"  # JSON array
    cities: str = "[]"  # JSON array
    remote_preference: str = "any"  # any/remote/hybrid/onsite
    min_experience: int = 0
    max_experience: int = 3
    salary_expectation: str = ""
    notice_period: str = ""
    base_resume_emphasis: str = ""  # description of what to emphasize
    allowed_portals: str = '["linkedin","naukri","workday"]'  # JSON array
    daily_cap: int = 50
    auto_apply_mode: str = "off"  # off/review/auto
    min_match_score: int = 60
    is_active: bool = True
