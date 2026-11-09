from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel

from models.base import TimestampMixin, utcnow


class AnswerBank(TimestampMixin, SQLModel, table=True):
    __tablename__ = "answerbank"

    id: Optional[int] = Field(default=None, primary_key=True)
    pattern: str = ""  # the question pattern/label
    category: str = ""  # general/legal/salary/authorization/demographic
    answer: str = ""
    approved: bool = False
    times_used: int = 0


class PortalAccount(TimestampMixin, SQLModel, table=True):
    __tablename__ = "portalaccount"

    id: Optional[int] = Field(default=None, primary_key=True)
    portal: str = ""  # linkedin/naukri/workday
    tenant: str = ""  # for workday company
    username: str = ""
    encrypted_password: str = ""  # Fernet encrypted
    is_active: bool = True
    last_login: Optional[datetime] = None


class Setting(SQLModel, table=True):
    __tablename__ = "setting"

    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(unique=True)
    value: str = ""
    category: str = "general"
    updated_at: datetime = Field(default_factory=utcnow)
