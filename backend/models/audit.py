from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LLMCall(SQLModel, table=True):
    __tablename__ = "llmcall"

    id: Optional[int] = Field(default=None, primary_key=True)
    provider: str = ""
    model: str = ""
    task: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    latency_ms: int = 0
    success: bool = True
    error: str = ""
    created_at: datetime = Field(default_factory=utcnow)


class AuditLog(SQLModel, table=True):
    __tablename__ = "auditlog"

    id: Optional[int] = Field(default=None, primary_key=True)
    action: str = ""
    entity_type: str = ""
    entity_id: Optional[int] = None
    details: str = ""
    created_at: datetime = Field(default_factory=utcnow)
