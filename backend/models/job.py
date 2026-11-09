from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel

from models.base import TimestampMixin, utcnow


class Job(TimestampMixin, SQLModel, table=True):
    __tablename__ = "job"

    id: Optional[int] = Field(default=None, primary_key=True)
    source: str = ""  # linkedin/naukri/workday
    external_id: str = ""
    title: str = ""
    company: str = ""
    location: str = ""
    url: str = ""
    description: str = ""
    posted_at: Optional[datetime] = None
    salary_info: str = ""
    experience_required: str = ""
    job_type: str = ""  # full-time, contract, etc.
    easy_apply: bool = False
    description_hash: str = ""
    status: str = "new"  # new/matched/applied/rejected/expired
    raw_data: str = ""  # JSON


class JobScore(SQLModel, table=True):
    __tablename__ = "jobscore"

    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="job.id")
    profile_id: int = Field(foreign_key="profile.id")
    score: int = 0
    reasons: str = ""  # JSON
    gaps: str = "[]"  # JSON array of missing skills
    red_flags: str = "[]"  # JSON array
    created_at: datetime = Field(default_factory=utcnow)
