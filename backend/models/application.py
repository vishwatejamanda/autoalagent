from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel

from models.base import TimestampMixin, utcnow


class Application(TimestampMixin, SQLModel, table=True):
    __tablename__ = "application"

    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="job.id")
    profile_id: int = Field(foreign_key="profile.id")
    resume_id: Optional[int] = None
    status: str = "pending"  # pending/submitted/review/failed/manual
    mode: str = "manual"
    applied_at: Optional[datetime] = None
    portal: str = ""
    screenshot_path: str = ""
    error_message: str = ""


class Resume(SQLModel, table=True):
    __tablename__ = "resume"

    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: Optional[int] = Field(default=None, foreign_key="job.id")
    profile_id: int = Field(foreign_key="profile.id")
    version: int = 1
    file_path: str = ""
    pdf_path: str = ""
    ats_score: int = 0
    is_base: bool = False
    tailoring_notes: str = ""
    created_at: datetime = Field(default_factory=utcnow)
